"""FastAPI router for laboratory booking and AI agent request endpoints.

Provides endpoints to query bookings, reserve equipment, update reservation statuses,
and a unified /api/request endpoint for AI agents.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tools.booking_tools import create_booking, get_bookings, update_booking
from tools.inventory_tools import check_inventory, get_equipment_status
from tools.scheduling_tools import check_availability

router = APIRouter(tags=["Bookings & Agent Requests"])


class BookingCreateRequest(BaseModel):
    equipment_id: Optional[str] = Field(None, description="Equipment ID (e.g. 'EQ-001')")
    equipment_name: Optional[str] = Field(None, description="Equipment name (e.g. 'Arduino Uno')")
    user_name: str = Field(..., description="Full name of the requester")
    start_time: str = Field(..., description="ISO 8601 start timestamp (e.g. '2026-08-21T14:00:00')")
    end_time: str = Field(..., description="ISO 8601 end timestamp (e.g. '2026-08-21T18:00:00')")
    quantity: int = Field(1, ge=1, description="Quantity of units to reserve")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    purpose: Optional[str] = Field(None, description="Experiment or workshop description")


class BookingUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="'CONFIRMED', 'ACTIVE', 'COMPLETED', or 'CANCELLED'")
    quantity: Optional[int] = Field(None, ge=1, description="Updated quantity")
    start_time: Optional[str] = Field(None, description="Updated start time")
    end_time: Optional[str] = Field(None, description="Updated end time")


class ResourceAgentRequest(BaseModel):
    action: Optional[str] = Field(
        None,
        description="Explicit action: 'check_inventory', 'get_status', 'check_availability', 'create_booking', 'update_booking', 'get_bookings'",
    )
    equipment_id: Optional[str] = None
    equipment_name: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    quantity: Optional[int] = 1
    category: Optional[str] = None
    purpose: Optional[str] = None
    booking_id: Optional[str] = None
    status: Optional[str] = None
    query: Optional[str] = None


@router.get("/api/bookings", summary="List laboratory bookings")
def list_bookings(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    equipment_id: Optional[str] = Query(None, description="Filter by equipment ID"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. ACTIVE, CONFIRMED, COMPLETED, CANCELLED)"),
):
    """Retrieve laboratory bookings with optional filtering."""
    return get_bookings(user_id=user_id, equipment_id=equipment_id, status=status)


@router.post("/api/bookings", status_code=201, summary="Create a new laboratory booking")
def new_booking(payload: BookingCreateRequest):
    """Reserve laboratory equipment for a designated time slot after checking availability."""
    target_eq = payload.equipment_id or payload.equipment_name
    if not target_eq:
        raise HTTPException(status_code=400, detail="Either 'equipment_id' or 'equipment_name' must be provided.")

    result = create_booking(
        equipment_identifier=target_eq,
        user_name=payload.user_name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        quantity=payload.quantity,
        user_id=payload.user_id,
        purpose=payload.purpose,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.patch("/api/bookings/{booking_id}", summary="Update a booking status or details")
def modify_booking(booking_id: str, payload: BookingUpdateRequest):
    """Update status, quantity, or time range for an existing booking."""
    result = update_booking(
        booking_id=booking_id,
        status=payload.status,
        quantity=payload.quantity,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404 if "not found" in result.get("error", "").lower() else 400, detail=result.get("error"))

    return result


@router.post("/api/request", summary="Unified AI agent request endpoint")
def handle_agent_request(req: ResourceAgentRequest) -> Dict[str, Any]:
    """Unified endpoint for LangChain and AI agents to dispatch laboratory queries and bookings.

    Dispatches dynamically based on the requested 'action' or payload parameters.
    """
    ident = req.equipment_id or req.equipment_name
    qty = req.quantity if (req.quantity and req.quantity > 0) else 1

    # 1. Action explicitly provided
    if req.action:
        action = req.action.lower().strip()
        if action in ("check_inventory", "inventory", "list"):
            return check_inventory(category=req.category, query=req.query)

        elif action in ("get_status", "status", "equipment"):
            if not ident:
                raise HTTPException(status_code=400, detail="equipment_id or equipment_name is required for status check.")
            return get_equipment_status(ident)

        elif action in ("check_availability", "availability"):
            if not ident:
                raise HTTPException(status_code=400, detail="equipment_id or equipment_name is required for availability check.")
            return check_availability(
                equipment_identifier=ident,
                start_time=req.start_time,
                end_time=req.end_time,
                quantity=qty,
            )

        elif action in ("create_booking", "book", "reserve"):
            if not ident:
                raise HTTPException(status_code=400, detail="equipment_id or equipment_name is required for booking.")
            if not req.user_name:
                raise HTTPException(status_code=400, detail="user_name is required for booking.")
            if not req.start_time or not req.end_time:
                raise HTTPException(status_code=400, detail="start_time and end_time are required for booking.")
            res = create_booking(
                equipment_identifier=ident,
                user_name=req.user_name,
                start_time=req.start_time,
                end_time=req.end_time,
                quantity=qty,
                user_id=req.user_id,
                purpose=req.purpose,
            )
            if not res.get("success"):
                raise HTTPException(status_code=400, detail=res)
            return res

        elif action in ("update_booking", "cancel_booking", "modify"):
            if not req.booking_id:
                raise HTTPException(status_code=400, detail="booking_id is required to update booking.")
            res = update_booking(
                booking_id=req.booking_id,
                status=req.status,
                quantity=req.quantity,
                start_time=req.start_time,
                end_time=req.end_time,
            )
            if not res.get("success"):
                raise HTTPException(status_code=400, detail=res)
            return res

        elif action in ("get_bookings", "bookings", "list_bookings"):
            return get_bookings(user_id=req.user_id, equipment_id=req.equipment_id, status=req.status)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: '{req.action}'.")

    # 2. Inferred action from parameters
    if req.booking_id and req.status:
        return update_booking(booking_id=req.booking_id, status=req.status)

    if ident and req.user_name and req.start_time and req.end_time:
        res = create_booking(
            equipment_identifier=ident,
            user_name=req.user_name,
            start_time=req.start_time,
            end_time=req.end_time,
            quantity=qty,
            user_id=req.user_id,
            purpose=req.purpose,
        )
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res)
        return res

    if ident and req.start_time and req.end_time:
        return check_availability(
            equipment_identifier=ident,
            start_time=req.start_time,
            end_time=req.end_time,
            quantity=qty,
        )

    if ident:
        return get_equipment_status(ident)

    if req.user_id or req.status:
        return get_bookings(user_id=req.user_id, equipment_id=req.equipment_id, status=req.status)

    # Fallback to general inventory check
    return check_inventory(category=req.category, query=req.query)
