"""
Data package for Smart Laboratory Resource Agent.
"""

from data.dummy_inventory import (
    Equipment,
    StudentProfile,
    ExistingReservation,
    DUMMY_EQUIPMENT,
    DUMMY_USERS,
    DUMMY_RESERVATIONS,
    get_equipment_by_id,
    get_equipment_by_name,
    get_user_profile,
    get_equipment_reservations,
)

__all__ = [
    "Equipment",
    "StudentProfile",
    "ExistingReservation",
    "DUMMY_EQUIPMENT",
    "DUMMY_USERS",
    "DUMMY_RESERVATIONS",
    "get_equipment_by_id",
    "get_equipment_by_name",
    "get_user_profile",
    "get_equipment_reservations",
]
