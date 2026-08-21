"""Auditor Agent for Smart Laboratory Resource Agent.

Verifies booking requests against laboratory safety guidelines, operational hours,
maximum duration policies, and equipment readiness.
Returns APPROVED or REJECTED with detailed audit justification.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AuditResult(BaseModel):
    """Structured response from the Auditor Agent."""
    status: str  # "APPROVED" or "REJECTED"
    approved: bool
    reason: str
    policy_violations: List[str] = Field(default_factory=list)
    audit_checks: Dict[str, bool] = Field(default_factory=dict)
    replan_suggestion: Optional[str] = None


class AuditorAgent:
    """Agent responsible for compliance, safety, and operational audit of lab reservations."""

    def __init__(
        self,
        max_duration_hours: float = 4.0,
        lab_open_hour: int = 8,
        lab_close_hour: int = 20
    ):
        self.max_duration_hours = max_duration_hours
        self.lab_open_hour = lab_open_hour
        self.lab_close_hour = lab_close_hour

    def _parse_time_to_minutes(self, t_str: str) -> int:
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def audit_booking(
        self,
        equipment_id: str,
        equipment_name: str,
        equipment_status: str,
        date: str,
        start_time: str,
        end_time: str,
        purpose: str,
        researcher: Optional[str] = None
    ) -> AuditResult:
        """Run policy and safety checks on a proposed lab booking."""
        violations: List[str] = []
        checks: Dict[str, bool] = {}
        replan_suggestions: List[str] = []

        # 1. Equipment Readiness Check
        is_operational = (equipment_status.upper() == "AVAILABLE")
        checks["equipment_operational"] = is_operational
        if not is_operational:
            violations.append(
                f"Equipment '{equipment_name}' ({equipment_id}) status is {equipment_status} (not operational)."
            )
            replan_suggestions.append("Select an alternative available equipment.")

        # 2. Time Ordering Check
        try:
            start_min = self._parse_time_to_minutes(start_time)
            end_min = self._parse_time_to_minutes(end_time)
            valid_time_order = (end_min > start_min)
        except Exception:
            valid_time_order = False
            start_min, end_min = 0, 0

        checks["valid_time_range"] = valid_time_order
        if not valid_time_order:
            violations.append(
                f"End time '{end_time}' must be strictly after start time '{start_time}'."
            )
            replan_suggestions.append("Adjust start and end time range.")

        # 3. Lab Operating Hours Check (08:00 - 20:00)
        open_min = self.lab_open_hour * 60
        close_min = self.lab_close_hour * 60
        within_hours = (start_min >= open_min and end_min <= close_min)
        checks["within_operating_hours"] = within_hours
        if not within_hours:
            violations.append(
                f"Booking time ({start_time} - {end_time}) falls outside lab operating hours "
                f"({self.lab_open_hour:02d}:00 - {self.lab_close_hour:02d}:00)."
            )
            replan_suggestions.append(
                f"Reschedule between {self.lab_open_hour:02d}:00 and {self.lab_close_hour:02d}:00."
            )

        # 4. Maximum Duration Policy Check (e.g. max 4 hours)
        duration_hours = (end_min - start_min) / 60.0 if valid_time_order else 0.0
        within_duration = (duration_hours <= self.max_duration_hours)
        checks["within_max_duration"] = within_duration
        if not within_duration:
            violations.append(
                f"Requested session duration of {duration_hours:.1f} hours exceeds the maximum lab policy "
                f"limit of {self.max_duration_hours:.1f} hours per booking."
            )
            replan_suggestions.append(
                f"Split or reduce booking duration to {self.max_duration_hours:.1f} hours or less."
            )

        # 5. Purpose Validity Check
        purpose_valid = bool(purpose and len(purpose.strip()) >= 5)
        checks["purpose_specified"] = purpose_valid
        if not purpose_valid:
            violations.append(
                "A clear research or experimental purpose must be stated for compliance auditing."
            )
            replan_suggestions.append("Provide a valid experimental purpose.")

        # Final Decision
        is_approved = (len(violations) == 0)
        status = "APPROVED" if is_approved else "REJECTED"

        if is_approved:
            reason = (
                f"Booking for '{equipment_name}' ({equipment_id}) on {date} from {start_time} to {end_time} "
                f"meets all lab safety, operational hours, duration limits, and compliance policies."
            )
            suggestion = None
        else:
            reason = f"Booking audit failed with {len(violations)} violation(s): " + " | ".join(violations)
            suggestion = " | ".join(replan_suggestions)

        return AuditResult(
            status=status,
            approved=is_approved,
            reason=reason,
            policy_violations=violations,
            audit_checks=checks,
            replan_suggestion=suggestion
        )
