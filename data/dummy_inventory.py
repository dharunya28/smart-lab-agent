"""
Dummy Laboratory Data: Equipment Inventory, User Profiles, and Current Reservations.
Used by Auditor Support and Integration Tests.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, time


@dataclass
class Equipment:
    equipment_id: str
    name: str
    category: str                         # Standard, High-Tier, Restricted
    tier: int                              # 1, 2, 3
    status: str                            # Available, In Maintenance, Under Calibration
    required_certification: str            # Required safety training code
    max_duration_hours: float              # Max allowable session duration
    min_duration_hours: float = 0.5        # Min allowable session duration
    requires_supervisor_approval: bool = False
    location: str = "Main Science Block"
    weekly_maintenance_window: Optional[str] = "Wed 12:00-14:00"


@dataclass
class StudentProfile:
    user_id: str
    name: str
    user_level: str                       # Undergraduate (L1), Postgraduate (L2), Faculty/Staff (L3)
    certifications: List[str]             # e.g., ["General Lab Safety 101", "Instrument Level 2 Training"]
    active_bookings_count: int = 0
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    no_show_count: int = 0


@dataclass
class ExistingReservation:
    reservation_id: str
    equipment_id: str
    user_id: str
    user_type: str                        # ClassSchedule, Postgraduate, Undergraduate
    priority_level: int                   # 1=Class (Highest), 2=Thesis Research, 3=Coursework, 4=Practice
    start_time: str                       # YYYY-MM-DD HH:MM
    end_time: str                         # YYYY-MM-DD HH:MM
    purpose: str


# ==========================================
# SEED LABORATORY INVENTORY
# ==========================================

DUMMY_EQUIPMENT: Dict[str, Equipment] = {
    "EQ-101": Equipment(
        equipment_id="EQ-101",
        name="Optical Microscope Leica DM750",
        category="Standard",
        tier=1,
        status="Available",
        required_certification="General Lab Safety 101",
        max_duration_hours=3.0,
        min_duration_hours=0.5,
        requires_supervisor_approval=False,
        location="Bio Lab 201",
    ),
    "EQ-102": Equipment(
        equipment_id="EQ-102",
        name="PCR Thermal Cycler Bio-Rad T100",
        category="Standard",
        tier=1,
        status="Available",
        required_certification="General Lab Safety 101",
        max_duration_hours=3.0,
        min_duration_hours=1.0,
        requires_supervisor_approval=False,
        location="Genetics Lab 204",
    ),
    "EQ-201": Equipment(
        equipment_id="EQ-201",
        name="High-Speed Refrigerated Centrifuge 5424R",
        category="High-Tier",
        tier=2,
        status="Available",
        required_certification="Instrument Level 2 Training",
        max_duration_hours=3.0,
        min_duration_hours=1.0,
        requires_supervisor_approval=False,
        location="Prep Room 105",
    ),
    "EQ-202": Equipment(
        equipment_id="EQ-202",
        name="UV-Vis Spectrophotometer Cary 60",
        category="High-Tier",
        tier=2,
        status="In Maintenance",
        required_certification="Instrument Level 2 Training",
        max_duration_hours=3.0,
        min_duration_hours=1.0,
        requires_supervisor_approval=False,
        location="Chem Lab 102",
    ),
    "EQ-301": Equipment(
        equipment_id="EQ-301",
        name="Scanning Electron Microscope (SEM) Zeiss Sigma",
        category="Restricted",
        tier=3,
        status="Available",
        required_certification="Instrument Level 3 Operator License",
        max_duration_hours=2.0,
        min_duration_hours=1.0,
        requires_supervisor_approval=True,
        location="Electron Microscopy Suite Basement B04",
    ),
    "EQ-401": Equipment(
        equipment_id="EQ-401",
        name="NMR 400MHz Spectrometer Bruker Avance",
        category="Restricted",
        tier=3,
        status="Available",
        required_certification="Instrument Level 3 Operator License",
        max_duration_hours=2.0,
        min_duration_hours=1.0,
        requires_supervisor_approval=True,
        location="NMR Facility Ground G12",
    ),
}


# ==========================================
# SEED STUDENT / USER PROFILES
# ==========================================

DUMMY_USERS: Dict[str, StudentProfile] = {
    "STU-001": StudentProfile(
        user_id="STU-001",
        name="Alice Walker",
        user_level="Undergraduate",
        certifications=["General Lab Safety 101"],
        active_bookings_count=1,
        is_suspended=False,
    ),
    "STU-002": StudentProfile(
        user_id="STU-002",
        name="Bob Chen",
        user_level="Postgraduate",
        certifications=["General Lab Safety 101", "Instrument Level 2 Training", "Instrument Level 3 Operator License"],
        active_bookings_count=0,
        is_suspended=False,
    ),
    "STU-003": StudentProfile(
        user_id="STU-003",
        name="Charlie Evans",
        user_level="Undergraduate",
        certifications=[],  # Has NOT completed basic lab safety!
        active_bookings_count=0,
        is_suspended=False,
    ),
    "STU-004": StudentProfile(
        user_id="STU-004",
        name="Diana Prince",
        user_level="Postgraduate",
        certifications=["General Lab Safety 101", "Instrument Level 2 Training"],
        active_bookings_count=3,  # Already at maximum 3 active quota
        is_suspended=False,
    ),
    "STU-005": StudentProfile(
        user_id="STU-005",
        name="Evan Wright",
        user_level="Undergraduate",
        certifications=["General Lab Safety 101"],
        active_bookings_count=0,
        is_suspended=True,
        suspension_reason="2 consecutive No-Shows on 2026-08-10",
        no_show_count=2,
    ),
}


# ==========================================
# SEED EXISTING RESERVATIONS
# ==========================================

DUMMY_RESERVATIONS: List[ExistingReservation] = [
    ExistingReservation(
        reservation_id="RES-1001",
        equipment_id="EQ-101",
        user_id="BIO-CLASS-201",
        user_type="ClassSchedule",
        priority_level=1,  # Academic Class (Highest)
        start_time="2026-08-22 10:00",
        end_time="2026-08-22 12:00",
        purpose="Biology 201 Practical Exam Demonstration",
    ),
    ExistingReservation(
        reservation_id="RES-1002",
        equipment_id="EQ-301",
        user_id="STU-002",
        user_type="Postgraduate",
        priority_level=2,  # Funded Thesis Research
        start_time="2026-08-22 14:00",
        end_time="2026-08-22 16:00",
        purpose="Nanomaterial Characterization for Thesis Defense",
    ),
]


def get_equipment_by_id(eq_id: str) -> Optional[Equipment]:
    """Look up equipment by ID (case-insensitive)."""
    return DUMMY_EQUIPMENT.get(eq_id.strip().upper())


def get_equipment_by_name(name_query: str) -> Optional[Equipment]:
    """Look up equipment by matching partial name."""
    query = name_query.lower()
    for eq in DUMMY_EQUIPMENT.values():
        if query in eq.name.lower() or query in eq.equipment_id.lower():
            return eq
    return None


def get_user_profile(user_id: str) -> Optional[StudentProfile]:
    """Look up user profile by ID (case-insensitive)."""
    return DUMMY_USERS.get(user_id.strip().upper())


def get_equipment_reservations(eq_id: str) -> List[ExistingReservation]:
    """Get all existing reservations for an equipment."""
    target_id = eq_id.strip().upper()
    return [r for r in DUMMY_RESERVATIONS if r.equipment_id == target_id]
