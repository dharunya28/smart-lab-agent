"""Database and persistence layer for Smart Laboratory Resource Agent.

Provides storage and retrieval for equipment inventory and bookings
using JSON files with support for SQLite synchronization.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EQUIPMENT_FILE = DATA_DIR / "equipment.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"

_lock = threading.Lock()


def _ensure_data_files() -> None:
    """Ensure data directory and JSON files exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not EQUIPMENT_FILE.exists():
        EQUIPMENT_FILE.write_text("[]", encoding="utf-8")
    if not BOOKINGS_FILE.exists():
        BOOKINGS_FILE.write_text("[]", encoding="utf-8")


def load_equipment() -> List[Dict[str, Any]]:
    """Load all equipment records from storage."""
    _ensure_data_files()
    with _lock:
        try:
            with open(EQUIPMENT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []


def save_equipment(equipment_list: List[Dict[str, Any]]) -> None:
    """Save equipment records to storage."""
    _ensure_data_files()
    with _lock:
        temp_file = EQUIPMENT_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(equipment_list, f, indent=2, ensure_ascii=False)
        temp_file.replace(EQUIPMENT_FILE)


def load_bookings() -> List[Dict[str, Any]]:
    """Load all bookings records from storage."""
    _ensure_data_files()
    with _lock:
        try:
            with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []


def save_bookings(bookings_list: List[Dict[str, Any]]) -> None:
    """Save bookings records to storage."""
    _ensure_data_files()
    with _lock:
        temp_file = BOOKINGS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(bookings_list, f, indent=2, ensure_ascii=False)
        temp_file.replace(BOOKINGS_FILE)


def get_equipment_by_id(equipment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an equipment item by its exact ID."""
    items = load_equipment()
    for item in items:
        if item.get("id", "").strip().lower() == equipment_id.strip().lower():
            return item
    return None


def find_equipment(identifier: str) -> Optional[Dict[str, Any]]:
    """Find equipment by exact ID or case-insensitive partial name match."""
    if not identifier:
        return None
    ident = identifier.strip().lower()
    items = load_equipment()

    # 1. Exact ID match
    for item in items:
        if item.get("id", "").strip().lower() == ident:
            return item

    # 2. Exact Name match (case-insensitive)
    for item in items:
        if item.get("name", "").strip().lower() == ident:
            return item

    # 3. Substring match in Name
    for item in items:
        if ident in item.get("name", "").strip().lower():
            return item

    # 4. Substring match in Category
    for item in items:
        if ident in item.get("category", "").strip().lower():
            return item

    return None


def search_equipment(
    category: Optional[str] = None,
    available_only: bool = False,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter equipment list based on category, availability, and search query."""
    items = load_equipment()
    results = []

    for item in items:
        # Category filter
        if category:
            cat = item.get("category", "").lower()
            if category.strip().lower() not in cat:
                continue

        # Available only filter
        if available_only:
            if item.get("available_quantity", 0) <= 0 or item.get("status") != "AVAILABLE":
                continue

        # Search query filter (matches ID, name, description, or category)
        if query:
            q = query.strip().lower()
            name = item.get("name", "").lower()
            eq_id = item.get("id", "").lower()
            desc = item.get("description", "").lower()
            cat = item.get("category", "").lower()

            if q not in name and q not in eq_id and q not in desc and q not in cat:
                continue

        results.append(item)

    return results


def update_equipment_quantity(equipment_id: str, available_delta: int) -> Optional[Dict[str, Any]]:
    """Adjust available quantity for equipment item."""
    items = load_equipment()
    updated_item = None

    for item in items:
        if item.get("id", "").strip().lower() == equipment_id.strip().lower():
            new_avail = max(0, item.get("available_quantity", 0) + available_delta)
            item["available_quantity"] = new_avail
            if new_avail == 0:
                item["status"] = "LOW_STOCK"
            elif item.get("status") == "LOW_STOCK" and new_avail > 0:
                item["status"] = "AVAILABLE"
            updated_item = item
            break

    if updated_item:
        save_equipment(items)

    return updated_item


def get_all_bookings(
    user_id: Optional[str] = None,
    equipment_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve bookings with optional filters."""
    bookings = load_bookings()
    results = []

    for b in bookings:
        if user_id and b.get("user_id", "").lower() != user_id.strip().lower():
            continue
        if equipment_id and b.get("equipment_id", "").lower() != equipment_id.strip().lower():
            continue
        if status and b.get("status", "").upper() != status.strip().upper():
            continue
        results.append(b)

    return results


def get_booking_by_id(booking_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve single booking by ID."""
    bookings = load_bookings()
    for b in bookings:
        if b.get("id", "").strip().lower() == booking_id.strip().lower():
            return b
    return None


def generate_booking_id() -> str:
    """Generate the next sequential booking ID."""
    bookings = load_bookings()
    max_num = 1000
    for b in bookings:
        b_id = b.get("id", "")
        if b_id.startswith("BK-"):
            try:
                num = int(b_id.split("-")[1])
                if num > max_num:
                    max_num = num
            except (IndexError, ValueError):
                pass
    return f"BK-{max_num + 1}"


def add_booking(booking: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new booking record."""
    if not booking.get("id"):
        booking["id"] = generate_booking_id()
    if not booking.get("created_at"):
        booking["created_at"] = datetime.now().isoformat()
    if not booking.get("status"):
        booking["status"] = "CONFIRMED"

    bookings = load_bookings()
    bookings.append(booking)
    save_bookings(bookings)
    return booking


def update_booking(booking_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update fields on an existing booking."""
    bookings = load_bookings()
    updated_booking = None

    for i, b in enumerate(bookings):
        if b.get("id", "").strip().lower() == booking_id.strip().lower():
            # Apply allowed updates
            for key, val in updates.items():
                if val is not None:
                    b[key] = val
            bookings[i] = b
            updated_booking = b
            break

    if updated_booking:
        save_bookings(bookings)

    return updated_booking
