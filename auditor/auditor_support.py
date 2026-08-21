"""
Auditor Support Module for Smart Laboratory Resource Agent.
Combines RAG laboratory rules, equipment inventory state, student profile,
and booking request data to determine APPROVED or REJECTED status with clear reasons.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Tuple
import os

from rag.rag_pipeline import LabRAGPipeline, get_rag_pipeline
from memory.memory import LabMemory, get_lab_memory
from data.dummy_inventory import (
    Equipment,
    StudentProfile,
    ExistingReservation,
    get_equipment_by_id,
    get_equipment_by_name,
    get_user_profile,
    get_equipment_reservations,
    DUMMY_RESERVATIONS,
)


@dataclass
class BookingRequest:
    """Incoming booking request details submitted by or for a student."""
    user_id: str
    equipment_id: str
    start_time: str                        # YYYY-MM-DD HH:MM
    end_time: str                          # YYYY-MM-DD HH:MM
    duration_hours: float
    purpose: str = "Academic Coursework"
    priority_level: int = 3                # 1=Class, 2=Thesis/Grant, 3=Coursework, 4=Practice
    supervisor_approved: bool = False
    after_hours_permit: bool = False
    request_text: Optional[str] = None     # Original natural language request


@dataclass
class AuditorDecision:
    """Auditor evaluation result with decision, explanation, and RAG rule citations."""
    status: str                            # APPROVED, REJECTED
    is_approved: bool
    reason: str                            # Human-readable clear explanation
    violated_rules: List[str] = field(default_factory=list)
    rag_citations: List[str] = field(default_factory=list)
    suggested_alternatives: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        """Returns a clean formatted audit report."""
        status_banner = "[APPROVED]" if self.is_approved else "[REJECTED]"
        lines = [
            f"================ AUDIT DECISION: {status_banner} ================",
            f"Timestamp: {self.evaluated_at}",
            f"Decision Reason: {self.reason}",
        ]
        if self.violated_rules:
            lines.append("\nViolated Policy Rules:")
            for rule in self.violated_rules:
                lines.append(f"  - {rule}")
        if self.suggested_alternatives:
            lines.append(f"\nSuggested Action / Alternatives:\n  {self.suggested_alternatives}")
        if self.rag_citations:
            lines.append("\nSupporting RAG Citations:")
            for cit in self.rag_citations:
                lines.append(f"  {cit}")
        lines.append("=" * 60)
        return "\n".join(lines)


class LabAuditor:
    """
    Core Auditor Engine.
    Evaluates booking requests against:
    1. RAG policy rules (operating hours, certification, duration limits, conflict priority, approvals)
    2. Dynamic laboratory inventory status & maintenance schedules
    3. User profiles and qualification status
    4. Existing schedule reservations
    """

    def __init__(
        self,
        rag_pipeline: Optional[LabRAGPipeline] = None,
        memory: Optional[LabMemory] = None,
    ):
        self.rag = rag_pipeline or get_rag_pipeline()
        self.memory = memory or get_lab_memory()

    def audit_booking(
        self,
        request: BookingRequest,
        record_to_memory: bool = True,
    ) -> AuditorDecision:
        """
        Performs a full multi-criteria audit on a laboratory booking request.
        Returns an AuditorDecision with status, reason, and RAG citations.
        """
        violations: List[str] = []
        citations: List[str] = []
        alternatives: Optional[str] = None
        conflict_detail: Optional[str] = None
        resolution_detail: Optional[str] = None

        # Fetch relevant entities
        user = get_user_profile(request.user_id)
        equipment = get_equipment_by_id(request.equipment_id)
        if not equipment:
            equipment = get_equipment_by_name(request.equipment_id)

        # -------------------------------------------------------------
        # 1. RAG Retrieval for Context
        # -------------------------------------------------------------
        rag_query = f"{request.equipment_id} booking rules operating hours duration certifications priority"
        retrieved_docs = self.rag.retrieve_relevant_rules(rag_query, k=2)
        for doc in retrieved_docs:
            src = doc.metadata.get("source", "Policy")
            sec = doc.metadata.get("section", "General")
            # Extract first 2 lines as concise citation
            snippet = "\n    ".join(doc.page_content.splitlines()[:4])
            citations.append(f"[{src} > {sec}]:\n    {snippet}...")

        # -------------------------------------------------------------
        # 2. Check User Status
        # -------------------------------------------------------------
        if not user:
            violations.append(f"Student ID '{request.user_id}' not found in registered lab user database.")
        else:
            if user.is_suspended:
                violations.append(
                    f"User account {user.user_id} ({user.name}) is currently SUSPENDED. Reason: {user.suspension_reason}."
                )
                alternatives = "Contact the Lab Safety Officer to appeal account suspension."

            if user.active_bookings_count >= 3:
                violations.append(
                    f"User has {user.active_bookings_count} active bookings. Policy limit is maximum 3 active bookings."
                )
                alternatives = "Wait until current bookings are completed or cancel an unused active booking."

        # -------------------------------------------------------------
        # 3. Check Equipment Status & Maintenance
        # -------------------------------------------------------------
        if not equipment:
            violations.append(f"Equipment '{request.equipment_id}' is not recognized in laboratory inventory.")
        else:
            if equipment.status.lower() != "available":
                violations.append(
                    f"Equipment '{equipment.name}' is currently '{equipment.status}' and cannot be scheduled."
                )
                alternatives = f"Check back after maintenance or select an alternative {equipment.category} instrument."

        # -------------------------------------------------------------
        # 4. Check Date, Operating Hours & Maintenance Windows
        # -------------------------------------------------------------
        try:
            start_dt = datetime.strptime(request.start_time, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(request.end_time, "%Y-%m-%d %H:%M")

            if end_dt <= start_dt:
                violations.append("End time must be strictly after start time.")

            # Sunday check (weekday 6 = Sunday)
            if start_dt.weekday() == 6:
                violations.append("Laboratory is CLOSED on Sundays for deep cleaning and facility maintenance.")
                alternatives = "Please schedule between Monday-Saturday during operational hours."

            # Saturday check (weekday 5 = Saturday: 09:00 - 17:00)
            elif start_dt.weekday() == 5:
                if start_dt.time() < time(9, 0) or end_dt.time() > time(17, 0):
                    violations.append(
                        f"Saturday operating hours are 09:00 to 17:00. Requested: {start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')}."
                    )
            # Weekday check (Mon-Fri: 08:00 - 20:00)
            else:
                is_after_hours = (start_dt.time() < time(8, 0)) or (end_dt.time() > time(20, 0))
                if is_after_hours:
                    if not request.after_hours_permit:
                        violations.append(
                            f"Booking outside standard hours (08:00 - 20:00) requires an approved After-Hours Access Permit."
                        )
                        alternatives = "Submit an After-Hours Access Permit to the Safety Officer 24 hours in advance."
                    elif user and user.user_level.lower() == "undergraduate":
                        violations.append(
                            "Undergraduates cannot work after-hours without a certified supervisor present in the lab."
                        )

            # Wednesday maintenance check (12:00 - 14:00)
            if equipment and equipment.tier in (2, 3) and start_dt.weekday() == 2:  # Wednesday
                m_start = time(12, 0)
                m_end = time(14, 0)
                if not (end_dt.time() <= m_start or start_dt.time() >= m_end):
                    violations.append(
                        f"Requested slot overlaps with mandatory weekly maintenance window (Wednesdays 12:00-14:00) for Tier {equipment.tier} instruments."
                    )
                    alternatives = "Select a slot on Wednesday before 12:00 or after 14:00."

        except ValueError as ve:
            violations.append(f"Invalid timestamp format (expected YYYY-MM-DD HH:MM): {ve}")

        # -------------------------------------------------------------
        # 5. Check Safety Training Certifications
        # -------------------------------------------------------------
        if user and equipment:
            req_cert = equipment.required_certification
            if req_cert not in user.certifications:
                violations.append(
                    f"User {user.name} lacks required certification '{req_cert}' for {equipment.name} (Tier {equipment.tier})."
                )
                alternatives = f"Complete the '{req_cert}' training module on the lab portal before booking."

        # -------------------------------------------------------------
        # 6. Check Duration Limits
        # -------------------------------------------------------------
        if equipment:
            if request.duration_hours > equipment.max_duration_hours:
                violations.append(
                    f"Requested duration ({request.duration_hours}h) exceeds maximum allowable limit of {equipment.max_duration_hours}h for {equipment.name}."
                )
                alternatives = f"Reduce booking slot duration to {equipment.max_duration_hours} hours or fewer."
            elif request.duration_hours < equipment.min_duration_hours:
                violations.append(
                    f"Requested duration ({request.duration_hours}h) is below minimum allowable duration of {equipment.min_duration_hours}h."
                )

        # -------------------------------------------------------------
        # 7. Check Supervisor Approval for Tier 3 Instruments
        # -------------------------------------------------------------
        if equipment and equipment.requires_supervisor_approval:
            if not request.supervisor_approved:
                violations.append(
                    f"{equipment.name} is a Restricted Tier 3 Instrument requiring verified Supervisor Approval sign-off."
                )
                alternatives = "Request your research advisor or faculty supervisor to approve the booking in the system."

        # -------------------------------------------------------------
        # 8. Check Existing Reservation Conflicts & Priority
        # -------------------------------------------------------------
        if equipment:
            existing_bookings = get_equipment_reservations(equipment.equipment_id)
            for ex in existing_bookings:
                # Check time overlap
                ex_start = datetime.strptime(ex.start_time, "%Y-%m-%d %H:%M")
                ex_end = datetime.strptime(ex.end_time, "%Y-%m-%d %H:%M")

                if 'start_dt' in locals() and 'end_dt' in locals():
                    # Overlap condition: start < ex_end and end > ex_start
                    if start_dt < ex_end and end_dt > ex_start:
                        conflict_detail = f"Slot overlaps with existing reservation {ex.reservation_id} ({ex.purpose}, booked by {ex.user_id})"
                        
                        # Priority Check: Lower priority level number = Higher actual priority
                        if ex.priority_level < request.priority_level:
                            violations.append(
                                f"Schedule Conflict: Slot is occupied by a higher-priority booking ({ex.purpose}, Priority Level {ex.priority_level} vs User Level {request.priority_level})."
                            )
                            alternatives = f"Choose a slot before {ex.start_time} or after {ex.end_time}."
                        elif ex.priority_level == request.priority_level:
                            violations.append(
                                f"Schedule Conflict: Slot already reserved by {ex.user_id} under first-come-first-served policy."
                            )
                            alternatives = f"Choose an open slot before {ex.start_time} or after {ex.end_time}."
                        else:
                            # Higher priority request bumps existing lower priority
                            resolution_detail = f"High-priority request (Level {request.priority_level}) can override lower-priority reservation {ex.reservation_id} (Level {ex.priority_level})."

        # -------------------------------------------------------------
        # Decision Synthesis
        # -------------------------------------------------------------
        if not violations:
            status = "APPROVED"
            is_approved = True
            reason = (
                f"Booking for '{equipment.name if equipment else request.equipment_id}' is APPROVED. "
                f"User certifications, operating hours ({request.start_time} to {request.end_time}), "
                f"duration ({request.duration_hours}h), and equipment availability criteria are all fully satisfied."
            )
            resolution_detail = resolution_detail or "Booking successfully approved and confirmed in schedule."
        else:
            status = "REJECTED"
            is_approved = False
            reason = f"Booking REJECTED due to {len(violations)} policy/operational violation(s): " + " | ".join(violations)
            resolution_detail = resolution_detail or "Booking rejected. Corrections required."

        decision = AuditorDecision(
            status=status,
            is_approved=is_approved,
            reason=reason,
            violated_rules=violations,
            rag_citations=citations,
            suggested_alternatives=alternatives,
        )

        # -------------------------------------------------------------
        # Record to Memory
        # -------------------------------------------------------------
        if record_to_memory:
            eq_name = equipment.name if equipment else request.equipment_id
            req_text = request.request_text or f"Book {eq_name} on {request.start_time} for {request.duration_hours}h"
            self.memory.add_interaction(
                user_id=request.user_id,
                request_text=req_text,
                equipment_id=request.equipment_id,
                equipment_name=eq_name,
                date_time=f"{request.start_time} to {request.end_time}",
                booking_result=status,
                previous_conflict=conflict_detail,
                final_resolution=resolution_detail,
                notes=reason,
            )

        return decision


# Module singleton helper
_DEFAULT_AUDITOR: Optional[LabAuditor] = None

def get_auditor() -> LabAuditor:
    """Returns or creates the shared LabAuditor instance."""
    global _DEFAULT_AUDITOR
    if _DEFAULT_AUDITOR is None:
        _DEFAULT_AUDITOR = LabAuditor()
    return _DEFAULT_AUDITOR
