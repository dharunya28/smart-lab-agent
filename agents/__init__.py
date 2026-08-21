"""Smart Laboratory Resource Agent Package.

Multi-agent AI system for laboratory resource scheduling, inventory checks,
conflict resolution, and compliance auditing.
"""

from .inventory_agent import InventoryAgent, LabInventoryBackendInterface
from .scheduling_agent import SchedulingAgent, LabSchedulingBackendInterface
from .conflict_agent import ConflictResolverAgent
from .auditor_agent import AuditorAgent
from .orchestrator import LabOrchestrator

__all__ = [
    "InventoryAgent",
    "LabInventoryBackendInterface",
    "SchedulingAgent",
    "LabSchedulingBackendInterface",
    "ConflictResolverAgent",
    "AuditorAgent",
    "LabOrchestrator",
]
