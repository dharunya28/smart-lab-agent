"""Scheduling and availability tools for Smart Laboratory Resource Agent.

Functions to verify equipment availability across time slots and detect booking conflicts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from backend.database import find_equipment, get_all_bookings


def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse various ISO-8601 formatted datetime strings."""
    if not dt_str:
        return None
    try:
        # Standard ISO parse (supports '2026-08-21T10:00:00' and '2026-08-21 10:00:00')
        cleaned = dt_str.replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        # Fallback date only
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None


def check_availability(
    equipment_identifier: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    quantity: int = 1,
) -> Dict[str, Any]:
    """Check whether specific laboratory equipment is available for a requested quantity and time window.

    Args:
        equipment_identifier: Equipment ID or name (e.g. 'EQ-001', 'Raspberry Pi', 'Oscilloscope').
        start_time: Optional ISO datetime string for start of booking slot (e.g. '2026-08-21T14:00:00').
        end_time: Optional ISO datetime string for end of booking slot (e.g. '2026-08-21T18:00:00').
        quantity: Number of units requested (default is 1).

    Returns:
        A dictionary with availability status, remaining capacity, and any conflicting bookings.
    """
    if not equipment_identifier or not equipment_identifier.strip():
        return {
            "success": False,
            "available": False,
            "error": "Equipment identifier must be provided.",
        }

    equipment = find_equipment(equipment_identifier)
    if not equipment:
        return {
            "success": False,
            "available": False,
            "error": f"Equipment '{equipment_identifier}' not found in laboratory inventory.",
        }

    eq_id = equipment["id"]
    total_qty = equipment.get("total_quantity", 0)
    current_avail = equipment.get("available_quantity", 0)

    if quantity <= 0:
        return {
            "success": False,
            "available": False,
            "error": "Requested quantity must be at least 1.",
        }

    # Case 1: Simple instant availability check (no specific time slot given)
    if not start_time or not end_time:
        is_avail = current_avail >= quantity
        return {
            "success": True,
            "available": is_avail,
            "equipment_id": eq_id,
            "equipment_name": equipment.get("name"),
            "requested_quantity": quantity,
            "current_available_quantity": current_avail,
            "total_quantity": total_qty,
            "message": (
                f"{quantity} unit(s) of '{equipment.get('name')}' are currently available."
                if is_avail
                else f"Insufficient quantity. Only {current_avail} of {total_qty} available currently."
            ),
        }

    # Case 2: Time slot availability check
    req_start = _parse_iso_datetime(start_time)
    req_end = _parse_iso_datetime(end_time)

    if not req_start or not req_end:
        return {
            "success": False,
            "available": False,
            "error": "Invalid start_time or end_time format. Use ISO format like '2026-08-21T14:00:00'.",
        }

    if req_start >= req_end:
        return {
            "success": False,
            "available": False,
            "error": "start_time must be strictly earlier than end_time.",
        }

    all_bookings = get_all_bookings(equipment_id=eq_id)
    conflicting_bookings: List[Dict[str, Any]] = []
    reserved_quantity = 0

    for b in all_bookings:
        if b.get("status") not in ("CONFIRMED", "ACTIVE"):
            continue

        b_start = _parse_iso_datetime(b.get("start_time", ""))
        b_end = _parse_iso_datetime(b.get("end_time", ""))

        if not b_start or not b_end:
            continue

        # Check for time interval overlap: (start1 < end2) and (end1 > start2)
        if b_start < req_end and b_end > req_start:
            conflicting_bookings.append(b)
            reserved_quantity += b.get("quantity", 1)

    available_for_slot = max(0, total_qty - reserved_quantity)
    is_available = available_for_slot >= quantity

    return {
        "success": True,
        "available": is_available,
        "equipment_id": eq_id,
        "equipment_name": equipment.get("name"),
        "requested_quantity": quantity,
        "start_time": req_start.isoformat(),
        "end_time": req_end.isoformat(),
        "total_quantity": total_qty,
        "reserved_in_slot": reserved_quantity,
        "available_for_slot": available_for_slot,
        "conflicting_bookings_count": len(conflicting_bookings),
        "conflicting_bookings": conflicting_bookings,
        "message": (
            f"'{equipment.get('name')}' is available ({available_for_slot} unit(s) remaining for requested slot)."
            if is_available
            else f"Unavailable: requested {quantity} unit(s), but only {available_for_slot} available during this slot."
        ),
    }


def find_next_available_slot(
    equipment_identifier: str,
    duration_hours: int = 2,
) -> Dict[str, Any]:
    """Find the next open booking slot for an equipment item."""
    equipment = find_equipment(equipment_identifier)
    if not equipment:
        return {
            "success": False,
            "error": f"Equipment '{equipment_identifier}' not found.",
        }

    now = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    slots_checked = 0
    # Search next 48 hours in 1-hour increments
    current_probe = now
    while slots_checked < 48:
        slot_end = current_probe + timedelta(hours=duration_hours)
        avail = check_availability(
            equipment_identifier=equipment["id"],
            start_time=current_probe.isoformat(),
            end_time=slot_end.isoformat(),
            quantity=1,
        )
        if avail.get("available"):
            return {
                "success": True,
                "equipment_id": equipment["id"],
                "equipment_name": equipment["name"],
                "suggested_start": current_probe.isoformat(),
                "suggested_end": slot_end.isoformat(),
                "available_quantity": avail.get("available_for_slot"),
            }
        current_probe += timedelta(hours=1)
        slots_checked += 1

    return {
        "success": False,
        "message": "No open slots found within the next 48 hours.",
    }
