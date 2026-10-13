"""Local JSON file storage engine for persistent memory."""

import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.app.core.config import get_settings
from backend.app.memory.models import MemoryRecord, MemoryUpdate, utcnow_iso

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe, atomic local JSON memory store."""

    def __init__(self, file_path: Optional[str] = None) -> None:
        settings = get_settings()
        self.file_path = Path(file_path or settings.MEMORY_FILE_PATH)
        self._lock = threading.RLock()
        self._ensure_storage_initialized()

    def _ensure_storage_initialized(self) -> None:
        """Create storage directory and initial JSON file if they do not exist."""
        with self._lock:
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                if not self.file_path.exists():
                    self._atomic_write({"memories": []})
                    logger.info(f"Initialized new persistent memory store at: {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to initialize memory file '{self.file_path}': {e}", exc_info=True)

    def _atomic_write(self, data: dict) -> None:
        """Write JSON atomically using a temporary file and rename."""
        parent_dir = self.file_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_fd, temp_path = tempfile.mkstemp(
            prefix=f"{self.file_path.name}.tmp.",
            dir=parent_dir,
            text=True,
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def load_all(self) -> List[MemoryRecord]:
        """Read all memory records from local JSON storage."""
        with self._lock:
            if not self.file_path.exists():
                return []

            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                records_data = data.get("memories", [])
                records = []
                for item in records_data:
                    try:
                        records.append(MemoryRecord.model_validate(item))
                    except Exception as parse_err:
                        logger.warning(f"Skipping malformed memory record: {parse_err}")
                return records

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Corrupted memory JSON encountered in '{self.file_path}': {e}")
                # Backup corrupt file
                backup_path = self.file_path.with_suffix(
                    f".corrupt.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                )
                try:
                    shutil.copy2(self.file_path, backup_path)
                    logger.info(f"Backed up corrupted memory file to: {backup_path}")
                except Exception as b_err:
                    logger.warning(f"Could not back up corrupt file: {b_err}")

                # Re-initialize clean memory store
                self._atomic_write({"memories": []})
                return []

    def save_all(self, memories: List[MemoryRecord]) -> None:
        """Persist a list of memory records to JSON storage."""
        with self._lock:
            payload = {
                "memories": [m.model_dump() for m in memories]
            }
            self._atomic_write(payload)

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        """Retrieve a specific memory by its ID."""
        memories = self.load_all()
        for m in memories:
            if m.id == memory_id:
                return m
        return None

    def add(self, memory: MemoryRecord) -> MemoryRecord:
        """Append a new memory record and persist."""
        with self._lock:
            memories = self.load_all()
            # Ensure unique ID
            memories = [m for m in memories if m.id != memory.id]
            memories.append(memory)
            self.save_all(memories)
            logger.info(f"Saved memory [{memory.id}] ({memory.category}): '{memory.content[:50]}...'")
            return memory

    def update(self, memory_id: str, updates: MemoryUpdate) -> Optional[MemoryRecord]:
        """Apply updates to an existing memory record."""
        with self._lock:
            memories = self.load_all()
            found = False
            updated_record = None

            for i, m in enumerate(memories):
                if m.id == memory_id:
                    updated_dict = m.model_dump()
                    if updates.content is not None:
                        updated_dict["content"] = updates.content.strip()
                    if updates.category is not None:
                        updated_dict["category"] = updates.category.strip().lower()
                    if updates.importance is not None:
                        updated_dict["importance"] = updates.importance
                    updated_dict["updated_at"] = utcnow_iso()

                    updated_record = MemoryRecord.model_validate(updated_dict)
                    memories[i] = updated_record
                    found = True
                    break

            if found:
                self.save_all(memories)
                logger.info(f"Updated memory [{memory_id}]")
                return updated_record
            return None

    def delete(self, memory_id: str) -> bool:
        """Delete a memory record by ID."""
        with self._lock:
            memories = self.load_all()
            initial_count = len(memories)
            memories = [m for m in memories if m.id != memory_id]
            if len(memories) < initial_count:
                self.save_all(memories)
                logger.info(f"Deleted memory [{memory_id}]")
                return True
            return False

    def clear(self) -> int:
        """Clear all stored memories and return count of deleted records."""
        with self._lock:
            memories = self.load_all()
            count = len(memories)
            self.save_all([])
            logger.info(f"Cleared {count} memories from persistent store")
            return count

    def touch(self, memory_id: str) -> None:
        """Update last_accessed_at timestamp and increment access_count."""
        with self._lock:
            memories = self.load_all()
            changed = False
            for m in memories:
                if m.id == memory_id:
                    m.last_accessed_at = utcnow_iso()
                    m.access_count += 1
                    changed = True
                    break
            if changed:
                self.save_all(memories)


# Global singleton memory store
memory_store = MemoryStore()
