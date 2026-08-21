"""Conflict Resolver Agent for Smart Laboratory Resource Agent.

Detects booking conflicts, finds optimal alternative slots, and generates
clear decision explanations.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ConflictDecision(BaseModel):
    """Structured response from the Conflict Resolver Agent."""
    has_conflict: bool
    decision: str  # "CONFIRMED_ORIGINAL", "ALTERNATIVE_RECOMMENDED", "NO_SLOT_AVAILABLE"
    conflict_reason: Optional[str] = None
    original_slot: Dict[str, str]
    recommended_slot: Optional[Dict[str, str]] = None
    available_alternatives: List[Dict[str, str]] = Field(default_factory=list)
    explanation: str


class ConflictResolverAgent:
    """Agent responsible for identifying booking clashes and finding optimal alternative slots."""

    def __init__(self):
        pass

    def _parse_time_to_minutes(self, t_str: str) -> int:
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def resolve(
        self,
        equipment_id: str,
        equipment_name: str,
        date: str,
        requested_start: str,
        requested_end: str,
        is_slot_free: bool,
        conflicting_bookings: List[Dict[str, Any]],
        available_slots: List[Dict[str, str]]
    ) -> ConflictDecision:
        """Analyze conflict state and select the best alternative slot if needed."""
        original_slot = {"start_time": requested_start, "end_time": requested_end}

        # Case 1: No conflict
        if is_slot_free and not conflicting_bookings:
            return ConflictDecision(
                has_conflict=False,
                decision="CONFIRMED_ORIGINAL",
                conflict_reason=None,
                original_slot=original_slot,
                recommended_slot=original_slot,
                available_alternatives=available_slots,
                explanation=(
                    f"No conflict detected for {equipment_name} ({equipment_id}) on {date} "
                    f"during {requested_start} - {requested_end}."
                )
            )

        # Case 2: Conflict exists
        conflict_details = []
        for b in conflicting_bookings:
            researcher = b.get("researcher", "Another researcher")
            start = b.get("start_time", "")
            end = b.get("end_time", "")
            purpose = b.get("purpose", "Laboratory session")
            conflict_details.append(f"Reserved by {researcher} ({start} - {end}) for '{purpose}'")

        conflict_reason = (
            f"The requested time {requested_start} - {requested_end} on {date} overlaps with: "
            + "; ".join(conflict_details)
        )

        if not available_slots:
            return ConflictDecision(
                has_conflict=True,
                decision="NO_SLOT_AVAILABLE",
                conflict_reason=conflict_reason,
                original_slot=original_slot,
                recommended_slot=None,
                available_alternatives=[],
                explanation=(
                    f"Conflict detected for {equipment_name} on {date}. "
                    f"No alternative slots are available within operating hours on this date."
                )
            )

        # Find closest alternative slot to requested_start
        req_start_min = self._parse_time_to_minutes(requested_start)

        def slot_distance(slot: Dict[str, str]) -> int:
            s_min = self._parse_time_to_minutes(slot["start_time"])
            # Prefer slots after requested time, but allow earlier if closest
            diff = s_min - req_start_min
            return abs(diff) + (1000 if diff < 0 else 0)

        sorted_alternatives = sorted(available_slots, key=slot_distance)
        best_alternative = sorted_alternatives[0]

        explanation = (
            f"Conflict detected for {equipment_name} on {date}: {conflict_reason}. "
            f"Alternative slot selected: {best_alternative['start_time']} - {best_alternative['end_time']} "
            f"as the closest open window on {date}."
        )

        return ConflictDecision(
            has_conflict=True,
            decision="ALTERNATIVE_RECOMMENDED",
            conflict_reason=conflict_reason,
            original_slot=original_slot,
            recommended_slot=best_alternative,
            available_alternatives=available_slots,
            explanation=explanation
        )
