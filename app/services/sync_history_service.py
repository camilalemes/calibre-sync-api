"""Sync History Service for tracking sync operations and results."""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SyncHistoryEntry:
    """Represents a single sync history entry."""
    
    def __init__(self, 
                 timestamp: datetime,
                 sync_type: str,
                 status: str,
                 duration: float,
                 library_path: str,
                 replica_paths: List[str],
                 results: Dict[str, Any],
                 error: Optional[str] = None):
        self.timestamp = timestamp
        self.sync_type = sync_type  # 'sync' or 'dry_run'
        self.status = status  # 'completed', 'failed', 'cancelled'
        self.duration = duration  # in seconds
        self.library_path = library_path
        self.replica_paths = replica_paths
        self.results = results
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'sync_type': self.sync_type,
            'status': self.status,
            'duration': self.duration,
            'library_path': self.library_path,
            'replica_paths': self.replica_paths,
            'results': self.results,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncHistoryEntry':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            sync_type=data['sync_type'],
            status=data['status'],
            duration=data['duration'],
            library_path=data['library_path'],
            replica_paths=data['replica_paths'],
            results=data['results'],
            error=data.get('error')
        )


class SyncHistoryService:
    """Service for managing sync history persistence."""
    
    def __init__(self, history_file_path: str = "/config/sync_history.json"):
        self.history_file_path = Path(history_file_path)
        self.max_entries = 100  # Keep last 100 sync operations
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the directory for the history file exists."""
        self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_history(self) -> List[SyncHistoryEntry]:
        """Load sync history from file."""
        if not self.history_file_path.exists():
            return []
        
        try:
            with open(self.history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [SyncHistoryEntry.from_dict(entry) for entry in data.get('entries', [])]
        except Exception as e:
            logger.error(f"Failed to load sync history: {e}")
            return []
    
    def _save_history(self, entries: List[SyncHistoryEntry]):
        """Save sync history to file."""
        try:
            # Keep only the most recent entries
            recent_entries = entries[-self.max_entries:] if len(entries) > self.max_entries else entries
            
            data = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'total_entries': len(recent_entries),
                'entries': [entry.to_dict() for entry in recent_entries]
            }
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.history_file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.history_file_path)
            logger.info(f"Saved sync history with {len(recent_entries)} entries")
            
        except Exception as e:
            logger.error(f"Failed to save sync history: {e}")
    
    def add_sync_entry(self, 
                      sync_type: str,
                      status: str,
                      duration: float,
                      library_path: str,
                      replica_paths: List[str],
                      results: Dict[str, Any],
                      error: Optional[str] = None) -> None:
        """Add a new sync entry to history."""
        
        entry = SyncHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            sync_type=sync_type,
            status=status,
            duration=duration,
            library_path=library_path,
            replica_paths=replica_paths,
            results=results,
            error=error
        )
        
        # Load existing history
        history = self._load_history()
        
        # Add new entry
        history.append(entry)
        
        # Save updated history
        self._save_history(history)
        
        logger.info(f"Added sync history entry: {sync_type} - {status} ({duration:.2f}s)")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get sync history entries."""
        entries = self._load_history()
        
        # Sort by timestamp (most recent first)
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit if specified
        if limit:
            entries = entries[:limit]
        
        return [entry.to_dict() for entry in entries]
    
    def get_latest_sync(self) -> Optional[Dict[str, Any]]:
        """Get the most recent sync entry."""
        history = self.get_history(limit=1)
        return history[0] if history else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sync history statistics."""
        entries = self._load_history()
        
        if not entries:
            return {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'last_sync': None,
                'average_duration': 0
            }
        
        successful = [e for e in entries if e.status == 'completed']
        failed = [e for e in entries if e.status == 'failed']
        
        # Calculate average duration for successful syncs
        avg_duration = 0
        if successful:
            avg_duration = sum(e.duration for e in successful) / len(successful)
        
        # Get most recent sync
        latest = max(entries, key=lambda x: x.timestamp)
        
        return {
            'total_syncs': len(entries),
            'successful_syncs': len(successful),
            'failed_syncs': len(failed),
            'last_sync': latest.to_dict(),
            'average_duration': round(avg_duration, 2)
        }
    
    def clear_history(self) -> None:
        """Clear all sync history."""
        try:
            if self.history_file_path.exists():
                self.history_file_path.unlink()
            logger.info("Sync history cleared")
        except Exception as e:
            logger.error(f"Failed to clear sync history: {e}")


# Global instance
_sync_history_service = None

def get_sync_history_service() -> SyncHistoryService:
    """Get the global sync history service instance."""
    global _sync_history_service
    if _sync_history_service is None:
        _sync_history_service = SyncHistoryService()
    return _sync_history_service