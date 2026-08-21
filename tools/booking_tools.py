"""Booking tools for Smart Laboratory Resource Agent.

Functions to query, create, and update laboratory equipment reservations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.database import (
    add_booking,
    find_equipment,
    get_all_bookings,
    get_booking_by_id,
    update_booking as db_update_booking,
    update_equipment_quantity,
)
from tools.scheduling_tools import check_availability


def get_bookings(
    user_id: Optional[str] = None,
    equipment_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve laboratory equipment bookings with optional filtering.

    Args:
        user_id: Filter bookings for a specific user ID.
        equipment_id: Filter bookings for a specific equipment ID.
        status: Filter by booking status ('ACTIVE', 'CONFIRMED', 'COMPLETED', 'CANCELLED').

    Returns:
        A dictionary containing the list of matching bookings and count.
    """
    bookings = get_all_bookings(user_id=user_id, equipment_id=equipment_id, status=status)
    return {
        "success": True,
        "total_found": len(bookings),
        "bookings": bookings,
    }


def create_booking(
    equipment_identifier: str,
    user_name: str,
    start_time: str,
    end_time: str,
    quantity: int = 1,
    user_id: Optional[str] = None,
    purpose: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new booking for a laboratory resource after validating availability.

    Args:
        equipment_identifier: Equipment ID or name (e.g. 'EQ-001', 'Arduino Uno').
        user_name: Full name of the user requesting the booking.
        start_time: ISO-8601 string for reservation start (e.g. '2026-08-21T14:00:00').
        end_time: ISO-8601 string for reservation end (e.g. '2026-08-21T18:00:00').
        quantity: Number of units requested (default 1).
        user_id: Optional user identifier (e.g. 'usr_102').
        purpose: Optional experiment or workshop description.

    Returns:
        A dictionary confirming booking creation or reporting conflict details.
    """
    if not user_name or not user_name.strip():
        return {
            "success": False,
            "error": "user_name is required to create a booking.",
        }

    equipment = find_equipment(equipment_identifier)
    if not equipment:
        return {
            "success": False,
            "error": f"Equipment '{equipment_identifier}' not found in laboratory inventory.",
        }

    # Verify time-slot availability
    avail_check = check_availability(
        equipment_identifier=equipment["id"],
        start_time=start_time,
        end_time=end_time,
        quantity=quantity,
    )

    if not avail_check.get("available"):
        return {
            "success": False,
            "error": "Equipment is not available for the requested time slot and quantity.",
            "availability_details": avail_check,
        }

    new_booking = {
        "equipment_id": equipment["id"],
        "equipment_name": equipment["name"],
        "user_name": user_name.strip(),
        "user_id": user_id.strip() if user_id else f"usr_{int(datetime.now().timestamp())}",
        "quantity": quantity,
        "start_time": avail_check.get("start_time", start_time),
        "end_time": avail_check.get("end_time", end_time),
        "status": "CONFIRMED",
        "purpose": purpose.strip() if purpose else "General Lab Experimentation",
    }

    created = add_booking(new_booking)

    return {
        "success": True,
        "message": f"Successfully booked {quantity} unit(s) of '{equipment['name']}' from {start_time} to {end_time}.",
        "booking": created,
    }


def update_booking(
    booking_id: str,
    status: Optional[str] = None,
    quantity: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing laboratory equipment booking.

    Args:
        booking_id: Unique identifier of the booking (e.g. 'BK-1001').
        status: New booking status ('ACTIVE', 'CONFIRMED', 'COMPLETED', 'CANCELLED').
        quantity: Updated quantity of units.
        start_time: Updated start time (ISO format).
        end_time: Updated end time (ISO format).

    Returns:
        A dictionary with the updated booking details.
    """
    if not booking_id or not booking_id.strip():
        return {
            "success": False,
            "error": "booking_id must be provided.",
        }

    existing = get_booking_by_id(booking_id)
    if not existing:
        return {
            "success": False,
            "error": f"Booking with ID '{booking_id}' was not found.",
        }

    updates: Dict[str, Any] = {}

    if status is not None:
        valid_statuses = ("CONFIRMED", "ACTIVE", "COMPLETED", "CANCELLED")
        norm_status = status.strip().upper()
        if norm_status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status '{status}'. Must be one of {valid_statuses}.",
            }
        updates["status"] = norm_status

    if quantity is not None:
        if quantity <= 0:
            return {
                "success": False,
                "error": "Quantity must be greater than 0.",
            }
        updates["quantity"] = quantity

    if start_time is not None:
        updates["start_time"] = start_time

    if end_time is not None:
        updates["end_time"] = end_time

    updated = db_update_booking(booking_id, updates)

    return {
        "success": True,
        "message": f"Booking '{booking_id}' has been updated successfully.",
        "booking": updated,
    }
