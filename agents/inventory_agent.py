"""Inventory Agent for Smart Laboratory Resource Agent.

Checks equipment availability, specifications, and operational status against
the laboratory inventory via a modular backend interface.
"""

from typing import Dict, List, Optional, Any
import os
from pydantic import BaseModel, Field


class EquipmentInfo(BaseModel):
    """Data model representing lab equipment."""
    equipment_id: str
    name: str
    category: str
    location: str
    status: str  # "AVAILABLE", "MAINTENANCE", "DECOMMISSIONED"
    is_operational: bool
    description: str
    aliases: List[str] = Field(default_factory=list)


class InventoryCheckResult(BaseModel):
    """Structured response for an inventory inquiry."""
    found: bool
    available: bool
    equipment_id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    message: str
    raw_data: Optional[Dict[str, Any]] = None


class LabInventoryBackendInterface:
    """Backend tool interface for lab inventory.

    Can be easily connected to a live database or REST API in production.
    Currently backed by structured dummy laboratory dataset.
    """

    def __init__(self):
        self._inventory: Dict[str, EquipmentInfo] = {
            "MIC-001": EquipmentInfo(
                equipment_id="MIC-001",
                name="Leica TCS SP8 Confocal Microscope",
                category="Imaging & Microscopy",
                location="Room 402 - Imaging Core",
                status="AVAILABLE",
                is_operational=True,
                description="High-resolution laser scanning confocal microscope for live and fixed fluorescence imaging.",
                aliases=["confocal microscope", "confocal", "leica confocal", "microscope"]
            ),
            "PCR-001": EquipmentInfo(
                equipment_id="PCR-001",
                name="Bio-Rad CFX96 Real-Time PCR Thermocycler",
                category="Molecular Biology",
                location="Room 305 - Genetics Lab",
                status="AVAILABLE",
                is_operational=True,
                description="96-well real-time PCR detection system for gene expression and quantification.",
                aliases=["pcr", "pcr machine", "rt-pcr", "thermocycler", "qpcr"]
            ),
            "HPLC-001": EquipmentInfo(
                equipment_id="HPLC-001",
                name="Agilent 1260 Infinity II HPLC System",
                category="Analytical Chemistry",
                location="Room 210 - Chromatography Lab",
                status="MAINTENANCE",
                is_operational=False,
                description="High-performance liquid chromatography system with UV-Vis diode array detector.",
                aliases=["hplc", "chromatography", "agilent hplc"]
            ),
            "CEN-001": EquipmentInfo(
                equipment_id="CEN-001",
                name="Eppendorf 5424R Refrigerated Microcentrifuge",
                category="Sample Preparation",
                location="Room 301 - General Lab",
                status="AVAILABLE",
                is_operational=True,
                description="High-speed microcentrifuge with temperature control from -9°C to 40°C.",
                aliases=["centrifuge", "microcentrifuge", "eppendorf centrifuge"]
            ),
            "FC-001": EquipmentInfo(
                equipment_id="FC-001",
                name="BD FACSAria III Flow Cytometer",
                category="Cell Biology",
                location="Room 412 - Flow Cytometry Suite",
                status="AVAILABLE",
                is_operational=True,
                description="Multi-laser cell sorter and analyzer for cell population phenotyping.",
                aliases=["flow cytometer", "facs", "cell sorter", "cytometer"]
            ),
            "SPEC-001": EquipmentInfo(
                equipment_id="SPEC-001",
                name="Thermo Scientific NanoDrop One UV-Vis Spectrophotometer",
                category="Biochemistry",
                location="Room 302 - Wet Lab",
                status="AVAILABLE",
                is_operational=True,
                description="Microvolume UV-Vis spectrophotometer for nucleic acid and protein quantification.",
                aliases=["spectrophotometer", "nanodrop", "uv-vis", "spec"]
            ),
            "AUTO-001": EquipmentInfo(
                equipment_id="AUTO-001",
                name="Tuttnauer 3870EL Autoclave Sterilizer",
                category="Sterilization",
                location="Room 108 - Wash Room",
                status="AVAILABLE",
                is_operational=True,
                description="Heavy-duty steam autoclave sterilizer for glassware and culture media.",
                aliases=["autoclave", "sterilizer", "steam autoclave"]
            )
        }

    def list_all_equipment(self) -> List[Dict[str, Any]]:
        """Return full list of registered laboratory equipment."""
        return [eq.model_dump() for eq in self._inventory.values()]

    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch equipment info by exact equipment ID."""
        eq = self._inventory.get(equipment_id.upper())
        return eq.model_dump() if eq else None

    def search_equipment(self, query: str) -> Optional[Dict[str, Any]]:
        """Search equipment by ID, exact name, or alias match."""
        query_norm = query.strip().lower()
        if not query_norm:
            return None

        # Check exact ID match
        if query_norm.upper() in self._inventory:
            return self._inventory[query_norm.upper()].model_dump()

        # Check exact name or alias match
        for eq in self._inventory.values():
            if query_norm == eq.name.lower():
                return eq.model_dump()
            if any(alias in query_norm or query_norm in alias for alias in eq.aliases):
                return eq.model_dump()

        # Fuzzy substring match on name
        for eq in self._inventory.values():
            if query_norm in eq.name.lower():
                return eq.model_dump()

        return None


class InventoryAgent:
    """Agent responsible for checking laboratory equipment inventory and operational readiness."""

    def __init__(self, backend: Optional[LabInventoryBackendInterface] = None):
        self.backend = backend or LabInventoryBackendInterface()

    def check_availability(self, equipment_query: str) -> InventoryCheckResult:
        """Evaluate whether requested equipment exists in inventory and is operational."""
        eq_data = self.backend.search_equipment(equipment_query)

        if not eq_data:
            return InventoryCheckResult(
                found=False,
                available=False,
                message=f"Equipment '{equipment_query}' was not found in the lab inventory."
            )

        equipment_id = eq_data["equipment_id"]
        name = eq_data["name"]
        status = eq_data["status"]
        is_operational = eq_data["is_operational"]
        location = eq_data["location"]

        if not is_operational or status != "AVAILABLE":
            return InventoryCheckResult(
                found=True,
                available=False,
                equipment_id=equipment_id,
                name=name,
                status=status,
                location=location,
                message=f"Equipment '{name}' ({equipment_id}) is currently {status} and not available for booking.",
                raw_data=eq_data
            )

        return InventoryCheckResult(
            found=True,
            available=True,
            equipment_id=equipment_id,
            name=name,
            status=status,
            location=location,
            message=f"Equipment '{name}' ({equipment_id}) is AVAILABLE in {location}.",
            raw_data=eq_data
        )
