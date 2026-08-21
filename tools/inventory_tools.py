"""Inventory tools for Smart Laboratory Resource Agent.

Functions to inspect laboratory inventory and check individual equipment status.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from backend.database import get_all_bookings, search_equipment, find_equipment


def check_inventory(
    category: Optional[str] = None,
    available_only: bool = False,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Check laboratory equipment inventory with optional filters.

    Args:
        category: Optional category to filter (e.g. 'Microcontrollers', 'Measurement & Testing').
        available_only: If True, only returns equipment currently in stock.
        query: Optional search keyword to match against name, category, or description.

    Returns:
        A dictionary containing matched equipment list and inventory summary.
    """
    items = search_equipment(category=category, available_only=available_only, query=query)

    total_units = sum(item.get("total_quantity", 0) for item in items)
    available_units = sum(item.get("available_quantity", 0) for item in items)

    return {
        "success": True,
        "total_found": len(items),
        "summary": {
            "total_equipment_types": len(items),
            "total_units": total_units,
            "available_units": available_units,
        },
        "items": items,
    }


def get_equipment_status(equipment_identifier: str) -> Dict[str, Any]:
    """Get the current operational status and availability of a specific lab equipment item.

    Args:
        equipment_identifier: Equipment ID (e.g. 'EQ-001') or equipment name (e.g. 'Arduino Uno', 'Oscilloscope').

    Returns:
        A dictionary containing detailed equipment information, current availability, and active bookings.
    """
    if not equipment_identifier or not equipment_identifier.strip():
        return {
            "success": False,
            "error": "Equipment identifier must not be empty.",
        }

    equipment = find_equipment(equipment_identifier)
    if not equipment:
        return {
            "success": False,
            "error": f"Equipment '{equipment_identifier}' not found in laboratory inventory.",
        }

    eq_id = equipment.get("id")
    all_bookings = get_all_bookings(equipment_id=eq_id)
    active_bookings = [b for b in all_bookings if b.get("status") in ("ACTIVE", "CONFIRMED")]

    return {
        "success": True,
        "equipment": equipment,
        "active_bookings_count": len(active_bookings),
        "active_bookings": active_bookings,
    }
