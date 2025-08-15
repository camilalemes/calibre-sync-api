import os
import shutil
import hashlib
import logging
import re
from typing import List, Dict, Optional, Set, Tuple
from ..config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sync_service")


class SyncService:
    def __init__(self, source_path: str, replica_paths: List[str]):
        """Initialize the sync service with source and replica paths."""
        self.source_path = source_path
        self.replica_paths = replica_paths

    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file for comparison."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_calibre_files(self) -> Dict[str, Dict]:
        """
        Create a dictionary of all files in the Calibre library.
        Maps relative paths to their metadata, preserving directory structure.
        """
        files_data = {}

        for root, dirs, files in os.walk(self.source_path):
            for filename in sorted(files):
                if filename.startswith('.'):
                    continue  # Skip hidden files but keep metadata.opf and cover.jpg

                filepath = os.path.join(root, filename)
                # Calculate relative path from source to preserve directory structure
                relative_path = os.path.relpath(filepath, self.source_path)
                
                try:
                    stat_info = os.stat(filepath)
                    # Use relative path as key to preserve directory structure
                    files_data[relative_path] = {
                        "path": filepath,
                        "size": stat_info.st_size,
                        "mtime": stat_info.st_mtime,
                        "relative_path": relative_path
                    }
                except OSError as e:
                    logger.error(f"Error accessing {filepath}: {e}")

        return files_data

    def get_replica_files(self, replica_path: str) -> Dict[str, Dict]:
        """
        Get a dictionary of file metadata from the replica.
        Keys are relative paths to preserve directory structure.
        """
        files_data = {}

        if not os.path.exists(replica_path):
            return files_data

        for root, dirs, files in os.walk(replica_path):
            for filename in sorted(files):
                if filename.startswith('.'):
                    continue

                filepath = os.path.join(root, filename)
                # Calculate relative path from replica root
                relative_path = os.path.relpath(filepath, replica_path)
                
                try:
                    stat_info = os.stat(filepath)
                    files_data[relative_path] = {
                        "path": filepath,
                        "size": stat_info.st_size,
                        "mtime": stat_info.st_mtime,
                        "relative_path": relative_path
                    }
                except OSError as e:
                    logger.error(f"Error accessing {filepath}: {e}")

        return files_data

    def get_destination_path(self, replica_path: str, original_file: Dict, dry_run: bool = False) -> str:
        """
        Determine the destination path in the replica preserving Calibre directory structure.
        """
        # Get the relative path from the source
        relative_path = original_file["relative_path"]
        destination_path = os.path.join(replica_path, relative_path)
        
        # Create directory structure if it doesn't exist
        if not dry_run:
            destination_dir = os.path.dirname(destination_path)
            os.makedirs(destination_dir, exist_ok=True)
        
        return destination_path

    def sync_folder(self, destination: str, dry_run: bool = False) -> Dict:
        """
        Sync from Calibre library to destination preserving directory structure.
        Returns stats about the operation.
        """
        logger.info(f"Starting sync from {self.source_path} to {destination}")

        # Ensure destination exists
        if not os.path.exists(destination):
            if not dry_run:
                os.makedirs(destination)
            logger.info(f"Created destination directory: {destination}")

        # Get file metadata for source and destination
        source_files = self.get_calibre_files()
        dest_files = self.get_replica_files(destination)

        # Track statistics
        stats = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "unchanged": 0,
            "ignored": 0,  # For files that are skipped (e.g., .db, .json)
            "errors": 0,
            # File lists for detailed reporting
            "added_files": [],
            "updated_files": [],
            "deleted_files": [],
            "ignored_files": [],
            "error_files": []
        }

        # Process source files - copy or update as needed
        processed_dest_files = set()

        for relative_path, source_meta in source_files.items():
            filename = os.path.basename(relative_path)
            
            # Handle different file types
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Skip .db and .json files except metadata.db
            if file_ext in ['.db', '.json'] and filename != 'metadata.db':
                stats["ignored"] += 1
                stats["ignored_files"].append(relative_path)
                logger.debug(f"Ignoring database/config file: {relative_path}")
                continue

            dest_path = self.get_destination_path(destination, source_meta, dry_run)
            
            # Keep track of processed files using relative paths
            processed_dest_files.add(relative_path)

            # Check if file exists in destination
            if relative_path not in dest_files:
                # File doesn't exist in destination, copy it
                if not dry_run:
                    try:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(source_meta["path"], dest_path)
                        stats["added"] += 1
                        stats["added_files"].append(relative_path)
                        logger.info(f"Added: {relative_path}")
                    except Exception as e:
                        stats["errors"] += 1
                        stats["error_files"].append(relative_path)
                        logger.error(f"Error copying {relative_path}: {e}")
                else:
                    stats["added"] += 1
                    stats["added_files"].append(relative_path)
                    logger.info(f"Would add: {relative_path}")
            else:
                # File exists, check if it's different
                dest_meta = dest_files[relative_path]

                if source_meta["size"] != dest_meta["size"] or \
                        abs(source_meta["mtime"] - dest_meta["mtime"]) > 1:  # Allow 1 second difference
                    # Different size or modification time, compare hashes for certainty
                    source_hash = self.calculate_file_hash(source_meta["path"])
                    dest_hash = self.calculate_file_hash(dest_meta["path"])

                    if source_hash != dest_hash:
                        if not dry_run:
                            try:
                                shutil.copy2(source_meta["path"], dest_path)
                                stats["updated"] += 1
                                stats["updated_files"].append(relative_path)
                                logger.info(f"Updated: {relative_path}")
                            except Exception as e:
                                stats["errors"] += 1
                                stats["error_files"].append(relative_path)
                                logger.error(f"Error updating {relative_path}: {e}")
                        else:
                            stats["updated"] += 1
                            stats["updated_files"].append(relative_path)
                            logger.info(f"Would update: {relative_path}")
                    else:
                        stats["unchanged"] += 1
                else:
                    stats["unchanged"] += 1

        # Find files to delete (in dest but not in source)
        for dest_relative_path, dest_meta in dest_files.items():
            if dest_relative_path not in processed_dest_files:
                # Never delete essential Calibre system files
                dest_filename = os.path.basename(dest_relative_path)
                if dest_filename in ['metadata.db', 'metadata_db_prefs_backup.json']:
                    logger.debug(f"Preserving Calibre system file: {dest_relative_path}")
                    continue
                
                if not dry_run:
                    try:
                        os.remove(dest_meta["path"])
                        stats["deleted"] += 1
                        stats["deleted_files"].append(dest_relative_path)
                        logger.info(f"Deleted: {dest_filename}")
                    except Exception as e:
                        stats["errors"] += 1
                        stats["error_files"].append(dest_filename)
                        logger.error(f"Error deleting {dest_filename}: {e}")
                else:
                    stats["deleted"] += 1
                    stats["deleted_files"].append(dest_filename)
                    logger.info(f"Would delete: {dest_filename}")

        logger.info(f"Sync completed. Stats: {stats}")
        return stats

    def sync_all(self, dry_run: bool = False) -> Dict[str, Dict]:
        """Sync the source to all replica destinations."""
        results = {}

        for replica in self.replica_paths:
            try:
                results[replica] = self.sync_folder(replica, dry_run)
            except Exception as e:
                logger.error(f"Failed to sync to {replica}: {e}")
                results[replica] = {"error": str(e)}

        return results


# Helper function to create a sync service from settings
def get_sync_service() -> SyncService:
    """Create a SyncService instance using settings."""
    return SyncService(
        source_path=settings.CALIBRE_LIBRARY_PATH,
        replica_paths=settings.replica_paths_list  # Use the property instead of REPLICA_PATHS directly
    )


# Function for direct use in scripts or API endpoints
def sync_folders(dry_run: bool = False) -> Dict[str, Dict]:
    """Synchronize the Calibre library to all replica locations."""
    sync_service = get_sync_service()
    return sync_service.sync_all(dry_run=dry_run)