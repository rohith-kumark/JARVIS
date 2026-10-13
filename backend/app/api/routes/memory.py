"""Memory API router providing full CRUD and search operations for long-term memory."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.memory.manager import memory_manager
from backend.app.memory.models import (
    MemoryCreate,
    MemoryListResponse,
    MemoryRecord,
    MemorySearchRequest,
    MemoryUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.get("", response_model=MemoryListResponse)
def get_all_memories(
    category: Optional[str] = Query(None, description="Optional category filter"),
) -> MemoryListResponse:
    """Retrieve all persistent memories, optionally filtered by category."""
    memories = memory_manager.get_all_memories(category=category)
    return MemoryListResponse(memories=memories, total=len(memories))


@router.get("/{memory_id}", response_model=MemoryRecord)
def get_memory_by_id(memory_id: str) -> MemoryRecord:
    """Retrieve a specific memory by its unique ID."""
    memory = memory_manager.get_memory(memory_id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return memory


@router.post("", response_model=MemoryRecord, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate) -> MemoryRecord:
    """Manually record a new user memory."""
    try:
        return memory_manager.add_memory(
            content=payload.content,
            category=payload.category or "other",
            importance=payload.importance if payload.importance is not None else 0.5,
            source=payload.source or "manual",
        )
    except Exception as e:
        logger.error(f"Failed to create memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to record memory: {str(e)}",
        )


@router.put("/{memory_id}", response_model=MemoryRecord)
def update_memory(memory_id: str, payload: MemoryUpdate) -> MemoryRecord:
    """Update fields of an existing memory record."""
    updated = memory_manager.update_memory(memory_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return updated


@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory(memory_id: str) -> dict:
    """Delete an individual memory record."""
    success = memory_manager.delete_memory(memory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return {"status": "success", "message": f"Memory {memory_id} deleted successfully"}


@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_memories() -> dict:
    """Clear all memories from persistent storage."""
    count = memory_manager.clear_memories()
    return {"status": "success", "message": f"Cleared {count} memories from storage"}


@router.post("/search", response_model=MemoryListResponse)
def search_memories(payload: MemorySearchRequest) -> MemoryListResponse:
    """Search for relevant memories based on query and optional category filter."""
    results = memory_manager.search_memories(
        query=payload.query,
        limit=payload.limit,
        category=payload.category,
    )
    return MemoryListResponse(memories=results, total=len(results))
