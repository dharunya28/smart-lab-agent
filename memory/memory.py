"""
Memory system for Smart Laboratory Resource Agent.
Stores and retrieves student interaction history, booking requests, conflict records, and resolutions.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import os
from typing import List, Optional, Dict, Any


@dataclass
class InteractionRecord:
    """Represents a single student-agent laboratory interaction."""
    interaction_id: str
    user_id: str                          # Student / User Identifier (e.g., STU-8821)
    timestamp: str                        # Recorded timestamp of interaction
    request_text: str                     # Natural language or parsed student request
    equipment_id: str                     # Equipment ID (e.g., EQ-301)
    equipment_name: str                   # Equipment Name (e.g., Scanning Electron Microscope)
    date_time: str                        # Requested booking date & time slot
    booking_result: str                   # APPROVED, REJECTED, CANCELLED, CONFLICT, PENDING
    previous_conflict: Optional[str] = None # Conflict details if any occurred
    final_resolution: Optional[str] = None  # How the booking or conflict was resolved
    notes: Optional[str] = None             # Auditor notes or rejection reason

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionRecord":
        return cls(**data)


class LabMemory:
    """
    In-memory and file-backed memory manager for student interactions and lab bookings.
    Provides fast lookup by student ID, conflict tracking, semantic/keyword search,
    and prompt-ready history formatting for LLM agents.
    """

    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file
        self._records: List[InteractionRecord] = []
        self._user_index: Dict[str, List[InteractionRecord]] = {}
        self._equipment_index: Dict[str, List[InteractionRecord]] = {}

        if self.storage_file and os.path.exists(self.storage_file):
            self.load_from_file(self.storage_file)

    def add_interaction(
        self,
        user_id: str,
        request_text: str,
        equipment_id: str,
        equipment_name: str,
        date_time: str,
        booking_result: str,
        previous_conflict: Optional[str] = None,
        final_resolution: Optional[str] = None,
        notes: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> InteractionRecord:
        """Records a new interaction in memory."""
        interaction_id = f"INT-{len(self._records) + 1:04d}"
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        record = InteractionRecord(
            interaction_id=interaction_id,
            user_id=user_id.strip().upper(),
            timestamp=timestamp,
            request_text=request_text.strip(),
            equipment_id=equipment_id.strip().upper(),
            equipment_name=equipment_name.strip(),
            date_time=date_time.strip(),
            booking_result=booking_result.strip().upper(),
            previous_conflict=previous_conflict.strip() if previous_conflict else None,
            final_resolution=final_resolution.strip() if final_resolution else None,
            notes=notes.strip() if notes else None,
        )

        self._records.append(record)

        # Update indexes
        uid = record.user_id
        if uid not in self._user_index:
            self._user_index[uid] = []
        self._user_index[uid].append(record)

        eid = record.equipment_id
        if eid not in self._equipment_index:
            self._equipment_index[eid] = []
        self._equipment_index[eid].append(record)

        if self.storage_file:
            self.save_to_file(self.storage_file)

        return record

    def get_user_history(self, user_id: str, limit: int = 10) -> List[InteractionRecord]:
        """Retrieves interaction history for a specific user, newest first."""
        uid = user_id.strip().upper()
        history = self._user_index.get(uid, [])
        return list(reversed(history))[:limit]

    def get_user_conflicts(self, user_id: str) -> List[InteractionRecord]:
        """Retrieves past interactions that involved booking conflicts for a user."""
        history = self.get_user_history(user_id, limit=50)
        return [r for r in history if r.previous_conflict or r.booking_result == "CONFLICT"]

    def get_equipment_history(self, equipment_id: str, limit: int = 10) -> List[InteractionRecord]:
        """Retrieves interaction history for a specific piece of equipment."""
        eid = equipment_id.strip().upper()
        history = self._equipment_index.get(eid, [])
        return list(reversed(history))[:limit]

    def get_recent_interactions(self, limit: int = 10) -> List[InteractionRecord]:
        """Retrieves all recent interactions across all users, newest first."""
        return list(reversed(self._records))[:limit]

    def search_interactions(
        self, query: str, user_id: Optional[str] = None, limit: int = 5
    ) -> List[InteractionRecord]:
        """Simple keyword search across requests, notes, equipment, and resolutions."""
        q_tokens = query.lower().split()
        pool = self.get_user_history(user_id, limit=100) if user_id else self._records

        scored = []
        for r in pool:
            searchable_text = f"{r.request_text} {r.equipment_name} {r.equipment_id} {r.previous_conflict or ''} {r.final_resolution or ''} {r.notes or ''}".lower()
            score = sum(1 for tok in q_tokens if tok in searchable_text)
            if score > 0:
                scored.append((score, r))

        # Sort by score desc, then recency
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def format_history_for_agent(self, user_id: str, limit: int = 5) -> str:
        """
        Formats user history into a clean markdown/text summary for agent context injection.
        """
        history = self.get_user_history(user_id, limit=limit)
        if not history:
            return f"No previous interaction history found for User: {user_id}."

        lines = [f"### Interaction History for User {user_id.upper()} (Last {len(history)} Events):"]
        for i, rec in enumerate(history, 1):
            conflict_info = f" | Conflict: {rec.previous_conflict}" if rec.previous_conflict else ""
            res_info = f" | Resolution: {rec.final_resolution}" if rec.final_resolution else ""
            note_info = f" | Notes: {rec.notes}" if rec.notes else ""
            lines.append(
                f"{i}. [{rec.timestamp}] Request: '{rec.request_text}' -> Equipment: {rec.equipment_name} ({rec.equipment_id}) for {rec.date_time}"
            )
            lines.append(
                f"   Result: **{rec.booking_result}**{conflict_info}{res_info}{note_info}"
            )
        return "\n".join(lines)

    def save_to_file(self, filepath: str) -> None:
        """Persists records to a JSON file."""
        data = [r.to_dict() for r in self._records]
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filepath: str) -> None:
        """Loads records from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._records = [InteractionRecord.from_dict(d) for d in data]
            self._user_index = {}
            self._equipment_index = {}
            for r in self._records:
                self._user_index.setdefault(r.user_id, []).append(r)
                self._equipment_index.setdefault(r.equipment_id, []).append(r)

    def clear(self) -> None:
        """Clears all stored memory."""
        self._records.clear()
        self._user_index.clear()
        self._equipment_index.clear()


# Module-level singleton helper
_DEFAULT_MEMORY: Optional[LabMemory] = None

def get_lab_memory() -> LabMemory:
    """Returns or creates the shared memory instance."""
    global _DEFAULT_MEMORY
    if _DEFAULT_MEMORY is None:
        _DEFAULT_MEMORY = LabMemory()
    return _DEFAULT_MEMORY
