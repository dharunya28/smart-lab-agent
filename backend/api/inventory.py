"""FastAPI router for laboratory inventory endpoints.

Provides endpoints to query laboratory equipment, filter by category/availability,
and inspect specific item statuses.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from tools.inventory_tools import check_inventory, get_equipment_status

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("", summary="Get laboratory inventory")
def list_inventory(
    category: Optional[str] = Query(None, description="Filter equipment by category"),
    available_only: bool = Query(False, description="Filter to only in-stock equipment"),
    query: Optional[str] = Query(None, description="Search keyword in name or description"),
):
    """Retrieve full or filtered laboratory equipment inventory."""
    result = check_inventory(category=category, available_only=available_only, query=query)
    return result


@router.get("/{equipment_identifier}", summary="Get equipment status by ID or name")
def get_single_equipment_status(equipment_identifier: str):
    """Retrieve operational status, availability, and active bookings for specific equipment."""
    result = get_equipment_status(equipment_identifier)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
