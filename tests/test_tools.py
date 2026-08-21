"""Unit tests for Smart Laboratory Agent tools."""

import pytest
from tools.inventory_tools import check_inventory, get_equipment_status
from tools.scheduling_tools import check_availability, find_next_available_slot
from tools.booking_tools import create_booking, get_bookings, update_booking


def test_check_inventory_all():
    res = check_inventory()
    assert res["success"] is True
    assert res["total_found"] > 0
    assert "items" in res
    assert "summary" in res
    assert res["summary"]["total_equipment_types"] >= 5


def test_check_inventory_filtered_category():
    res = check_inventory(category="Microcontrollers")
    assert res["success"] is True
    for item in res["items"]:
        assert "microcontroller" in item["category"].lower()


def test_check_inventory_query():
    res = check_inventory(query="Oscilloscope")
    assert res["success"] is True
    assert len(res["items"]) >= 1
    assert "Oscilloscope" in res["items"][0]["name"]


def test_get_equipment_status_by_id_and_name():
    # ID lookup
    res_id = get_equipment_status("EQ-001")
    assert res_id["success"] is True
    assert res_id["equipment"]["id"] == "EQ-001"
    assert "Arduino" in res_id["equipment"]["name"]

    # Name lookup (case-insensitive partial)
    res_name = get_equipment_status("raspberry")
    assert res_name["success"] is True
    assert res_name["equipment"]["id"] == "EQ-002"

    # Non-existent
    res_none = get_equipment_status("NonExistentItemXYZ")
    assert res_none["success"] is False
    assert "not found" in res_none["error"].lower()


def test_check_availability():
    # Instant check
    avail_instant = check_availability("EQ-001", quantity=1)
    assert avail_instant["success"] is True
    assert "available" in avail_instant

    # Time slot check
    slot_check = check_availability(
        equipment_identifier="Arduino",
        start_time="2026-08-25T10:00:00",
        end_time="2026-08-25T14:00:00",
        quantity=2,
    )
    assert slot_check["success"] is True
    assert slot_check["available"] is True


def test_check_availability_invalid_dates():
    # start after end
    res = check_availability("EQ-001", start_time="2026-08-25T14:00:00", end_time="2026-08-25T10:00:00")
    assert res["available"] is False
    assert "earlier" in res["error"].lower()


def test_create_and_update_booking():
    # Create booking
    res = create_booking(
        equipment_identifier="EQ-004",
        user_name="Test Scientist",
        start_time="2026-08-26T09:00:00",
        end_time="2026-08-26T11:00:00",
        quantity=1,
        purpose="Sensor calibration test",
    )
    assert res["success"] is True
    assert "booking" in res
    booking_id = res["booking"]["id"]
    assert booking_id.startswith("BK-")

    # Update booking
    up_res = update_booking(booking_id=booking_id, status="CANCELLED")
    assert up_res["success"] is True
    assert up_res["booking"]["status"] == "CANCELLED"


def test_get_bookings():
    res = get_bookings()
    assert res["success"] is True
    assert res["total_found"] > 0
    assert isinstance(res["bookings"], list)


def test_find_next_available_slot():
    res = find_next_available_slot("Arduino", duration_hours=2)
    assert res["success"] is True
    assert "suggested_start" in res
    assert "suggested_end" in res
