import datetime
import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel

from ..services.sync_service import sync_folders, get_sync_service
from ..services.sync_history_service import get_sync_history_service

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)

# Keep track of sync status
sync_status = {
    "last_sync": None,
    "in_progress": False,
    "result": None,
    "errors": None
}


class SyncResponse(BaseModel):
    status: str
    last_sync: datetime.datetime | None = None
    details: Dict[str, Any] | None = None


def perform_sync(dry_run: bool = False):
    global sync_status
    
    start_time = time.time()
    history_service = get_sync_history_service()
    sync_service = get_sync_service()
    
    try:
        sync_status["in_progress"] = True
        sync_status["result"] = None
        sync_status["errors"] = None

        # Run the sync
        result = sync_folders(dry_run=dry_run)
        duration = time.time() - start_time

        logger.info(f"Sync completed. Result: {result}")
        sync_status["result"] = result
        sync_status["last_sync"] = datetime.datetime.now()
        
        # Record successful sync in history
        history_service.add_sync_entry(
            sync_type="dry_run" if dry_run else "sync",
            status="completed",
            duration=duration,
            library_path=sync_service.source_path,
            replica_paths=sync_service.replica_paths,
            results=result
        )
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        
        logger.error(f"Error during sync: {error_msg}")
        logger.exception(e)
        sync_status["errors"] = error_msg
        
        # Record failed sync in history
        history_service.add_sync_entry(
            sync_type="dry_run" if dry_run else "sync",
            status="failed",
            duration=duration,
            library_path=sync_service.source_path,
            replica_paths=sync_service.replica_paths,
            results={},
            error=error_msg
        )
        
    finally:
        sync_status["in_progress"] = False


@router.post("/trigger", response_model=SyncResponse)
async def trigger_sync(
        background_tasks: BackgroundTasks,
        dry_run: bool = Query(False, description="Run in dry-run mode without making changes")
):
    if sync_status["in_progress"]:
        return SyncResponse(
            status="already_running",
            last_sync=sync_status["last_sync"]
        )

    background_tasks.add_task(perform_sync, dry_run=dry_run)

    return SyncResponse(
        status="started",
        last_sync=sync_status["last_sync"]
    )

@router.get("/status", response_model=SyncResponse)
async def get_sync_status():
    """Get the current sync status"""
    return SyncResponse(
        status="in_progress" if sync_status["in_progress"] else "idle",
        last_sync=sync_status["last_sync"],
        details={
            "result": sync_status["result"],
            "errors": sync_status["errors"]
        }
    )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_sync_history(limit: Optional[int] = Query(20, description="Maximum number of history entries to return")):
    """Get sync history with optional limit"""
    history_service = get_sync_history_service()
    return history_service.get_history(limit=limit)


@router.get("/history/stats", response_model=Dict[str, Any])
async def get_sync_stats():
    """Get sync history statistics"""
    history_service = get_sync_history_service()
    return history_service.get_stats()


@router.get("/history/latest", response_model=Optional[Dict[str, Any]])
async def get_latest_sync():
    """Get the most recent sync entry"""
    history_service = get_sync_history_service()
    return history_service.get_latest_sync()


@router.delete("/history")
async def clear_sync_history():
    """Clear all sync history"""
    history_service = get_sync_history_service()
    history_service.clear_history()
    return {"message": "Sync history cleared successfully"}