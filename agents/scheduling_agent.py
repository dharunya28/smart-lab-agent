"""Scheduling Agent for Smart Laboratory Resource Agent.

Verifies requested dates/times against the lab equipment schedule and
retrieves open time windows via a backend tool interface.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, time
from pydantic import BaseModel, Field


class BookingSlot(BaseModel):
    """Represents a time slot."""
    start_time: str  # Format: "HH:MM" e.g., "10:00"
    end_time: str    # Format: "HH:MM" e.g., "12:00"


class ExistingBooking(BaseModel):
    """Represents an active lab booking."""
    booking_id: str
    equipment_id: str
    date: str        # Format: "YYYY-MM-DD" e.g., "2026-08-25"
    start_time: str
    end_time: str
    researcher: str
    purpose: str


class ScheduleCheckResult(BaseModel):
    """Structured response from the Scheduling Agent."""
    equipment_id: str
    date: str
    requested_start: str
    requested_end: str
    is_available: bool
    conflicting_bookings: List[Dict[str, Any]] = Field(default_factory=list)
    available_slots: List[Dict[str, str]] = Field(default_factory=list)
    message: str


class LabSchedulingBackendInterface:
    """Backend tool interface for lab calendar & scheduling operations.

    Maintains lab operating schedule and dummy existing reservations.
    """

    def __init__(self):
        # Lab operating hours
        self.opening_hour = 8   # 08:00
        self.closing_hour = 20  # 20:00

        # Dummy seed bookings
        self._bookings: List[ExistingBooking] = [
            # Confocal Microscope bookings on 2026-08-25
            ExistingBooking(
                booking_id="BK-1001",
                equipment_id="MIC-001",
                date="2026-08-25",
                start_time="10:00",
                end_time="12:00",
                researcher="Dr. Sarah Jenkins",
                purpose="Confocal live-cell imaging of neuroblastoma lines"
            ),
            ExistingBooking(
                booking_id="BK-1002",
                equipment_id="MIC-001",
                date="2026-08-25",
                start_time="15:00",
                end_time="17:00",
                researcher="Alex Rivera",
                purpose="GFP fluorescence intensity measurements"
            ),
            # PCR Thermocycler bookings on 2026-08-25
            ExistingBooking(
                booking_id="BK-1003",
                equipment_id="PCR-001",
                date="2026-08-25",
                start_time="09:00",
                end_time="11:30",
                researcher="Dr. Emily Chen",
                purpose="qPCR verification of CRISPR knockouts"
            ),
            # Flow Cytometer bookings on 2026-08-25
            ExistingBooking(
                booking_id="BK-1004",
                equipment_id="FC-001",
                date="2026-08-25",
                start_time="13:00",
                end_time="16:00",
                researcher="Carlos Gomez",
                purpose="Immune cell surface marker panel screening"
            ),
        ]

    def _parse_time_to_minutes(self, t_str: str) -> int:
        """Convert HH:MM string to minutes from midnight."""
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _minutes_to_time_str(self, minutes: int) -> str:
        """Convert minutes from midnight to HH:MM format."""
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    def get_bookings_for_date(self, equipment_id: str, date: str) -> List[ExistingBooking]:
        """Fetch all existing bookings for a specific equipment and date."""
        return [
            b for b in self._bookings
            if b.equipment_id.upper() == equipment_id.upper() and b.date == date
        ]

    def check_slot_overlap(
        self, equipment_id: str, date: str, start_time: str, end_time: str
    ) -> List[ExistingBooking]:
        """Return any existing bookings overlapping with the requested window."""
        req_start = self._parse_time_to_minutes(start_time)
        req_end = self._parse_time_to_minutes(end_time)

        bookings = self.get_bookings_for_date(equipment_id, date)
        overlaps = []

        for b in bookings:
            b_start = self._parse_time_to_minutes(b.start_time)
            b_end = self._parse_time_to_minutes(b.end_time)

            # Check overlap condition: (StartA < EndB) and (EndA > StartB)
            if req_start < b_end and req_end > b_start:
                overlaps.append(b)

        return overlaps

    def find_available_slots(
        self, equipment_id: str, date: str, slot_duration_minutes: int = 120
    ) -> List[Dict[str, str]]:
        """Find open continuous time slots within operating hours for given equipment and date."""
        bookings = self.get_bookings_for_date(equipment_id, date)

        # Sort bookings by start time
        sorted_bookings = sorted(
            bookings, key=lambda b: self._parse_time_to_minutes(b.start_time)
        )

        open_slots: List[Dict[str, str]] = []
        current_time = self.opening_hour * 60
        closing_time = self.closing_hour * 60

        for b in sorted_bookings:
            b_start = self._parse_time_to_minutes(b.start_time)
            b_end = self._parse_time_to_minutes(b.end_time)

            # Check gap before this booking
            if b_start - current_time >= slot_duration_minutes:
                # Add valid slots in this gap
                slot_start = current_time
                while slot_start + slot_duration_minutes <= b_start:
                    open_slots.append({
                        "start_time": self._minutes_to_time_str(slot_start),
                        "end_time": self._minutes_to_time_str(slot_start + slot_duration_minutes)
                    })
                    slot_start += 60  # Shift by 1-hour step for alternative options

            current_time = max(current_time, b_end)

        # Check gap between last booking and closing time
        if closing_time - current_time >= slot_duration_minutes:
            slot_start = current_time
            while slot_start + slot_duration_minutes <= closing_time:
                open_slots.append({
                    "start_time": self._minutes_to_time_str(slot_start),
                    "end_time": self._minutes_to_time_str(slot_start + slot_duration_minutes)
                })
                slot_start += 60

        return open_slots


class SchedulingAgent:
    """Agent responsible for checking lab calendar slots and identifying open windows."""

    def __init__(self, backend: Optional[LabSchedulingBackendInterface] = None):
        self.backend = backend or LabSchedulingBackendInterface()

    def check_schedule(
        self,
        equipment_id: str,
        date: str,
        start_time: str,
        end_time: str
    ) -> ScheduleCheckResult:
        """Check if requested slot is available and list existing conflicts and alternative slots."""
        # Calculate duration in minutes
        req_start_min = self.backend._parse_time_to_minutes(start_time)
        req_end_min = self.backend._parse_time_to_minutes(end_time)
        duration_min = max(30, req_end_min - req_start_min)

        overlapping_bookings = self.backend.check_slot_overlap(
            equipment_id=equipment_id,
            date=date,
            start_time=start_time,
            end_time=end_time
        )

        available_slots = self.backend.find_available_slots(
            equipment_id=equipment_id,
            date=date,
            slot_duration_minutes=duration_min
        )

        is_available = (len(overlapping_bookings) == 0)

        if is_available:
            msg = f"Requested slot {start_time} - {end_time} on {date} for {equipment_id} is free."
        else:
            conflict_names = [f"{b.researcher} ({b.start_time}-{b.end_time})" for b in overlapping_bookings]
            msg = f"Slot {start_time} - {end_time} on {date} has conflicts with: {', '.join(conflict_names)}."

        return ScheduleCheckResult(
            equipment_id=equipment_id,
            date=date,
            requested_start=start_time,
            requested_end=end_time,
            is_available=is_available,
            conflicting_bookings=[b.model_dump() for b in overlapping_bookings],
            available_slots=available_slots,
            message=msg
        )
