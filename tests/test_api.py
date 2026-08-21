"""Integration tests for FastAPI laboratory backend endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_inventory():
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_found"] > 0
    assert len(data["items"]) > 0


def test_get_inventory_with_filters():
    response = client.get("/api/inventory?category=Prototyping")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert all("prototyping" in item["category"].lower() for item in data["items"])


def test_get_inventory_single_item():
    response = client.get("/api/inventory/EQ-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["equipment"]["id"] == "EQ-001"


def test_get_inventory_item_not_found():
    response = client.get("/api/inventory/nonexistent-item-999")
    assert response.status_code == 404


def test_get_bookings():
    response = client.get("/api/bookings")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["bookings"], list)


def test_create_booking_via_api():
    payload = {
        "equipment_id": "EQ-005",
        "user_name": "Dr. Strange",
        "start_time": "2026-08-27T10:00:00",
        "end_time": "2026-08-27T12:00:00",
        "quantity": 1,
        "purpose": "Quantum circuit prototyping",
    }
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["booking"]["user_name"] == "Dr. Strange"
    booking_id = data["booking"]["id"]

    # Patch booking
    patch_res = client.patch(f"/api/bookings/{booking_id}", json={"status": "COMPLETED"})
    assert patch_res.status_code == 200
    assert patch_res.json()["booking"]["status"] == "COMPLETED"


def test_agent_request_endpoint_inventory():
    payload = {
        "action": "check_inventory",
        "query": "Arduino",
    }
    response = client.post("/api/request", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert any("Arduino" in item["name"] for item in data["items"])


def test_agent_request_endpoint_availability():
    payload = {
        "action": "check_availability",
        "equipment_name": "Arduino Uno Rev3",
        "start_time": "2026-08-28T09:00:00",
        "end_time": "2026-08-28T11:00:00",
        "quantity": 2,
    }
    response = client.post("/api/request", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["available"] is True


def test_agent_request_endpoint_smart_booking():
    payload = {
        "equipment_name": "Raspberry Pi 4 Model B (4GB)",
        "user_name": "Tony Stark",
        "start_time": "2026-08-29T10:00:00",
        "end_time": "2026-08-29T16:00:00",
        "quantity": 1,
        "purpose": "AI Lab Edge inference",
    }
    response = client.post("/api/request", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["booking"]["equipment_id"] == "EQ-002"
