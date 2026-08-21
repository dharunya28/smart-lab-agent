# Smart Laboratory Resource Agent - Backend

Backend service and agent tools for managing laboratory equipment inventory, scheduling, and bookings. Designed to integrate with LangChain AI agents.

---

## Project Structure

```
smart-lab-agent/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint & middleware
│   ├── database.py              # Storage layer with persistence & CRUD operations
│   └── api/
│       ├── __init__.py
│       ├── inventory.py         # /api/inventory endpoints
│       └── booking.py           # /api/bookings and /api/request endpoints
├── tools/
│   ├── __init__.py              # Tool exports for LangChain agents
│   ├── inventory_tools.py       # check_inventory(), get_equipment_status()
│   ├── booking_tools.py         # get_bookings(), create_booking(), update_booking()
│   └── scheduling_tools.py      # check_availability(), find_next_available_slot()
├── data/
│   ├── equipment.json           # Realistic laboratory equipment dummy data
│   └── bookings.json            # Laboratory booking reservations data
├── tests/
│   ├── test_tools.py            # Unit tests for tool functions
│   └── test_api.py              # Integration tests for FastAPI endpoints
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Installation & Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the FastAPI Server:**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   Interactive Swagger docs are available at `http://localhost:8000/docs`.

---

## Tool Functions (for LangChain & Agents)

All tool functions can be directly imported and wrapped as LangChain `@tool` or executed in custom agent loops:

```python
from tools import (
    check_inventory,
    get_equipment_status,
    get_bookings,
    check_availability,
    create_booking,
    update_booking,
    find_next_available_slot
)

# 1. Check inventory
result = check_inventory(category="Microcontrollers", available_only=True)

# 2. Get equipment status by name or ID
status = get_equipment_status("Arduino Uno")

# 3. Check time-slot availability
avail = check_availability(
    equipment_identifier="Oscilloscope",
    start_time="2026-08-25T10:00:00",
    end_time="2026-08-25T14:00:00",
    quantity=1
)

# 4. Create a booking
booking = create_booking(
    equipment_identifier="Raspberry Pi",
    user_name="Alice Johnson",
    start_time="2026-08-25T14:00:00",
    end_time="2026-08-25T18:00:00",
    quantity=2,
    purpose="Edge AI Workshop"
)

# 5. Update a booking
update_booking(booking_id="BK-1001", status="COMPLETED")

# 6. List bookings
bookings = get_bookings(status="ACTIVE")
```

---

## REST API Endpoints

### 1. `GET /api/inventory`
Query parameters:
- `category` (optional): Filter by category (e.g. `Microcontrollers`, `Measurement & Testing`, `Sensors & Actuators`, `Prototyping`).
- `available_only` (optional): `true` / `false`
- `query` (optional): Search keyword in name, id, or description.

### 2. `GET /api/inventory/{equipment_id}`
Returns details, operational status, and active bookings for the specified item (by ID or name).

### 3. `GET /api/bookings`
Query parameters:
- `user_id` (optional)
- `equipment_id` (optional)
- `status` (optional: `ACTIVE`, `CONFIRMED`, `COMPLETED`, `CANCELLED`)

### 4. `POST /api/bookings`
Create a booking:
```json
{
  "equipment_id": "EQ-001",
  "user_name": "Alice Johnson",
  "start_time": "2026-08-22T10:00:00",
  "end_time": "2026-08-22T14:00:00",
  "quantity": 2,
  "purpose": "Sensor Interface Lab"
}
```

### 5. `PATCH /api/bookings/{booking_id}`
Update status or time:
```json
{
  "status": "CANCELLED"
}
```

### 6. `POST /api/request` (Unified AI Agent Endpoint)
Single unified endpoint supporting flexible agent actions:
```json
{
  "action": "check_availability",
  "equipment_name": "Digital Storage Oscilloscope",
  "start_time": "2026-08-22T14:00:00",
  "end_time": "2026-08-22T18:00:00",
  "quantity": 1
}
```

---

## Running Tests

```bash
pytest -v
```
