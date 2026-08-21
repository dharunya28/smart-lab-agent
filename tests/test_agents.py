"""Unit tests for Smart Laboratory Resource Agent AI Layer."""

import unittest
from agents import (
    InventoryAgent,
    SchedulingAgent,
    ConflictResolverAgent,
    AuditorAgent,
    LabOrchestrator,
)


class TestInventoryAgent(unittest.TestCase):
    def setUp(self):
        self.agent = InventoryAgent()

    def test_available_equipment(self):
        res = self.agent.check_availability("Confocal Microscope")
        self.assertTrue(res.found)
        self.assertTrue(res.available)
        self.assertEqual(res.equipment_id, "MIC-001")

    def test_maintenance_equipment(self):
        res = self.agent.check_availability("HPLC")
        self.assertTrue(res.found)
        self.assertFalse(res.available)
        self.assertEqual(res.status, "MAINTENANCE")

    def test_unknown_equipment(self):
        res = self.agent.check_availability("Quantum Supercollider")
        self.assertFalse(res.found)
        self.assertFalse(res.available)


class TestSchedulingAgent(unittest.TestCase):
    def setUp(self):
        self.agent = SchedulingAgent()

    def test_slot_free(self):
        res = self.agent.check_schedule("MIC-001", "2026-08-25", "12:00", "14:00")
        self.assertTrue(res.is_available)
        self.assertEqual(len(res.conflicting_bookings), 0)

    def test_slot_conflict(self):
        res = self.agent.check_schedule("MIC-001", "2026-08-25", "10:00", "12:00")
        self.assertFalse(res.is_available)
        self.assertGreater(len(res.conflicting_bookings), 0)
        self.assertGreater(len(res.available_slots), 0)


class TestConflictResolverAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ConflictResolverAgent()

    def test_resolve_without_conflict(self):
        decision = self.agent.resolve(
            equipment_id="MIC-001",
            equipment_name="Confocal Microscope",
            date="2026-08-25",
            requested_start="12:00",
            requested_end="14:00",
            is_slot_free=True,
            conflicting_bookings=[],
            available_slots=[]
        )
        self.assertFalse(decision.has_conflict)
        self.assertEqual(decision.decision, "CONFIRMED_ORIGINAL")

    def test_resolve_with_conflict(self):
        conflicts = [{"researcher": "Dr. Sarah Jenkins", "start_time": "10:00", "end_time": "12:00", "purpose": "Imaging"}]
        slots = [{"start_time": "12:00", "end_time": "14:00"}, {"start_time": "17:00", "end_time": "19:00"}]
        decision = self.agent.resolve(
            equipment_id="MIC-001",
            equipment_name="Confocal Microscope",
            date="2026-08-25",
            requested_start="10:00",
            requested_end="12:00",
            is_slot_free=False,
            conflicting_bookings=conflicts,
            available_slots=slots
        )
        self.assertTrue(decision.has_conflict)
        self.assertEqual(decision.decision, "ALTERNATIVE_RECOMMENDED")
        self.assertEqual(decision.recommended_slot["start_time"], "12:00")


class TestAuditorAgent(unittest.TestCase):
    def setUp(self):
        self.agent = AuditorAgent()

    def test_audit_approved(self):
        res = self.agent.audit_booking(
            equipment_id="PCR-001",
            equipment_name="PCR Thermocycler",
            equipment_status="AVAILABLE",
            date="2026-08-25",
            start_time="10:00",
            end_time="12:00",
            purpose="qPCR gene expression assays"
        )
        self.assertTrue(res.approved)
        self.assertEqual(res.status, "APPROVED")

    def test_audit_duration_violation(self):
        res = self.agent.audit_booking(
            equipment_id="PCR-001",
            equipment_name="PCR Thermocycler",
            equipment_status="AVAILABLE",
            date="2026-08-25",
            start_time="10:00",
            end_time="16:00",  # 6 hours > 4 hours max
            purpose="Long duration run"
        )
        self.assertFalse(res.approved)
        self.assertEqual(res.status, "REJECTED")
        self.assertFalse(res.audit_checks["within_max_duration"])

    def test_audit_operating_hours_violation(self):
        res = self.agent.audit_booking(
            equipment_id="PCR-001",
            equipment_name="PCR Thermocycler",
            equipment_status="AVAILABLE",
            date="2026-08-25",
            start_time="06:00",  # Before 08:00
            end_time="08:00",
            purpose="Early morning run"
        )
        self.assertFalse(res.approved)
        self.assertFalse(res.audit_checks["within_operating_hours"])


class TestLabOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = LabOrchestrator()

    def test_orchestrator_replan_loop(self):
        # 6 hours request will trigger auditor rejection and automatic replan down to 4 hours
        req = "Book the PCR Thermocycler on 2026-08-25 from 12:00 to 18:00 for gene amplification"
        res = self.orchestrator.process_request(req)
        self.assertEqual(res.status, "CONFIRMED_WITH_REPLAN")
        self.assertEqual(res.replan_count, 1)
        self.assertEqual(res.final_booking.start_time, "12:00")
        self.assertEqual(res.final_booking.end_time, "16:00")


if __name__ == "__main__":
    unittest.main()
