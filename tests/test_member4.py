"""
Comprehensive Unit & Integration Test Suite for Member 4:
- RAG Knowledge Base & Retrieval
- Interaction Memory & Conflict Tracking
- Auditor Support Engine (Approved / Rejected Decisions)
"""

import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag.rag_pipeline import LabRAGPipeline, LocalSemanticEmbeddings
from memory.memory import LabMemory, InteractionRecord
from data.dummy_inventory import (
    get_equipment_by_id,
    get_user_profile,
    DUMMY_EQUIPMENT,
    DUMMY_USERS,
)
from auditor.auditor_support import LabAuditor, BookingRequest, AuditorDecision


class TestLabRAGPipeline(unittest.TestCase):
    """Tests for the RAG Knowledge Base and LangChain-based retrieval."""

    @classmethod
    def setUpClass(cls):
        cls.rag = LabRAGPipeline()

    def test_document_indexing(self):
        """Verify that all policy files are loaded and chunked."""
        self.assertGreater(len(self.rag.documents), 10, "Expected at least 10 chunks from rule files.")
        sources = {doc.metadata.get("source") for doc in self.rag.documents}
        self.assertIn("lab_rules.txt", sources)
        self.assertIn("equipment_rules.txt", sources)
        self.assertIn("booking_policy.txt", sources)

    def test_retrieve_operating_hours(self):
        """Verify relevant retrieval for lab operating hours query."""
        results = self.rag.retrieve_relevant_rules("What are the laboratory operating hours and weekend schedule?", k=3)
        self.assertTrue(len(results) > 0)
        content_text = " ".join([d.page_content for d in results]).lower()
        self.assertTrue("operating hours" in content_text or "08:00" in content_text or "20:00" in content_text)

    def test_retrieve_duration_limits(self):
        """Verify relevant retrieval for SEM equipment booking limits."""
        results = self.rag.retrieve_relevant_rules("What is the maximum booking duration for the Scanning Electron Microscope SEM?", k=3)
        self.assertTrue(len(results) > 0)
        content_text = " ".join([d.page_content for d in results]).lower()
        self.assertTrue("duration" in content_text or "sem" in content_text or "tier 3" in content_text or "hours" in content_text)

    def test_get_rules_context_formatted(self):
        """Verify context string formatting for LLM agent prompts."""
        context = self.rag.get_rules_context("conflict resolution priority rules", k=2)
        self.assertIsInstance(context, str)
        self.assertIn("--- Rule Citation", context)


class TestLabMemory(unittest.TestCase):
    """Tests for the student interaction memory system."""

    def setUp(self):
        self.memory = LabMemory()

    def test_add_and_get_user_history(self):
        """Verify adding interactions and retrieving by student ID."""
        self.memory.add_interaction(
            user_id="STU-001",
            request_text="Book Leica Microscope tomorrow at 10 AM",
            equipment_id="EQ-101",
            equipment_name="Optical Microscope Leica DM750",
            date_time="2026-08-22 10:00 to 11:30",
            booking_result="APPROVED",
            notes="Valid booking within operating hours",
        )

        history = self.memory.get_user_history("STU-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].user_id, "STU-001")
        self.assertEqual(history[0].booking_result, "APPROVED")
        self.assertEqual(history[0].equipment_id, "EQ-101")

    def test_conflict_history_retrieval(self):
        """Verify filtering for interactions that had conflicts."""
        self.memory.add_interaction(
            user_id="STU-002",
            request_text="Book SEM at 14:00",
            equipment_id="EQ-301",
            equipment_name="Scanning Electron Microscope",
            date_time="2026-08-22 14:00 to 16:00",
            booking_result="CONFLICT",
            previous_conflict="Overlapped with Thesis defense slot",
            final_resolution="Rescheduled to 16:30",
        )
        self.memory.add_interaction(
            user_id="STU-002",
            request_text="Book Centrifuge at 09:00",
            equipment_id="EQ-201",
            equipment_name="Centrifuge",
            date_time="2026-08-23 09:00 to 10:00",
            booking_result="APPROVED",
        )

        conflicts = self.memory.get_user_conflicts("STU-002")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].previous_conflict, "Overlapped with Thesis defense slot")
        self.assertEqual(conflicts[0].final_resolution, "Rescheduled to 16:30")

    def test_search_interactions(self):
        """Verify keyword search in memory."""
        self.memory.add_interaction(
            user_id="STU-001",
            request_text="Need PCR Cycler for genetics experiment",
            equipment_id="EQ-102",
            equipment_name="PCR Thermal Cycler",
            date_time="2026-08-24 11:00 to 13:00",
            booking_result="APPROVED",
        )
        results = self.memory.search_interactions("genetics PCR")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].equipment_id, "EQ-102")

    def test_format_history_for_agent(self):
        """Verify markdown string formatting for agent prompt injection."""
        self.memory.add_interaction(
            user_id="STU-001",
            request_text="Book Microscope",
            equipment_id="EQ-101",
            equipment_name="Optical Microscope Leica DM750",
            date_time="2026-08-22 10:00 to 11:30",
            booking_result="APPROVED",
        )
        formatted = self.memory.format_history_for_agent("STU-001")
        self.assertIn("STU-001", formatted)
        self.assertIn("Optical Microscope Leica DM750", formatted)
        self.assertIn("APPROVED", formatted)


class TestLabAuditor(unittest.TestCase):
    """Tests for Auditor decision engine (Approved vs Rejected)."""

    def setUp(self):
        self.memory = LabMemory()
        self.auditor = LabAuditor(memory=self.memory)

    def test_valid_booking_approved(self):
        """Scenario 1: Standard booking fully compliant -> APPROVED."""
        req = BookingRequest(
            user_id="STU-001",                   # Has Safety 101
            equipment_id="EQ-101",               # Optical Microscope (Tier 1, Available)
            start_time="2026-08-25 14:00",       # Tuesday 14:00 (Within hours)
            end_time="2026-08-25 15:30",         # Duration 1.5h (<= 3h limit)
            duration_hours=1.5,
            purpose="Biology Coursework",
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "APPROVED")
        self.assertTrue(decision.is_approved)
        self.assertEqual(len(decision.violated_rules), 0)
        self.assertTrue(len(decision.rag_citations) > 0)

    def test_operating_hours_violation_sunday(self):
        """Scenario 2: Booking on Sunday (closed) -> REJECTED."""
        req = BookingRequest(
            user_id="STU-001",
            equipment_id="EQ-101",
            start_time="2026-08-23 10:00",       # Sunday
            end_time="2026-08-23 11:00",
            duration_hours=1.0,
            purpose="Sunday test",
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertFalse(decision.is_approved)
        self.assertTrue(any("CLOSED on Sundays" in v for v in decision.violated_rules))

    def test_missing_certification_violation(self):
        """Scenario 3: Student lacks required Tier 2/3 certification -> REJECTED."""
        req = BookingRequest(
            user_id="STU-003",                   # Charlie Evans has no certifications
            equipment_id="EQ-101",               # Requires General Lab Safety 101
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 11:00",
            duration_hours=1.0,
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("lacks required certification" in v for v in decision.violated_rules))

    def test_exceeded_duration_limit_violation(self):
        """Scenario 4: Request duration 4h exceeds 2h max limit for SEM -> REJECTED."""
        req = BookingRequest(
            user_id="STU-002",                   # Has Tier 3 License
            equipment_id="EQ-301",               # SEM max duration = 2.0h
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 14:00",
            duration_hours=4.0,                  # Exceeds limit
            supervisor_approved=True,
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("exceeds maximum allowable limit" in v for v in decision.violated_rules))

    def test_equipment_in_maintenance_violation(self):
        """Scenario 5: Equipment marked 'In Maintenance' -> REJECTED."""
        req = BookingRequest(
            user_id="STU-002",
            equipment_id="EQ-202",               # UV-Vis Spectrophotometer is 'In Maintenance'
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 11:00",
            duration_hours=1.0,
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("In Maintenance" in v for v in decision.violated_rules))

    def test_schedule_conflict_with_class(self):
        """Scenario 6: Conflict with higher priority academic class -> REJECTED."""
        req = BookingRequest(
            user_id="STU-001",
            equipment_id="EQ-101",
            start_time="2026-08-22 10:30",       # Overlaps with BIO-CLASS-201 (10:00 - 12:00)
            end_time="2026-08-22 11:30",
            duration_hours=1.0,
            priority_level=3,                   # Coursework (Priority 3 vs Class Priority 1)
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("Schedule Conflict" in v for v in decision.violated_rules))

    def test_suspended_user_rejection(self):
        """Scenario 7: Suspended user -> REJECTED."""
        req = BookingRequest(
            user_id="STU-005",                   # Evan Wright is suspended
            equipment_id="EQ-101",
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 11:00",
            duration_hours=1.0,
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("SUSPENDED" in v for v in decision.violated_rules))

    def test_tier3_requires_supervisor_approval(self):
        """Scenario 8: Tier 3 equipment without supervisor approval -> REJECTED."""
        req = BookingRequest(
            user_id="STU-002",                   # Has Tier 3 License
            equipment_id="EQ-301",               # SEM
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 12:00",
            duration_hours=2.0,
            supervisor_approved=False,          # Missing supervisor sign-off
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("Supervisor Approval" in v for v in decision.violated_rules))

    def test_tier3_with_supervisor_approval_approved(self):
        """Scenario 9: Tier 3 equipment WITH supervisor approval and license -> APPROVED."""
        req = BookingRequest(
            user_id="STU-002",
            equipment_id="EQ-301",
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 12:00",
            duration_hours=2.0,
            supervisor_approved=True,           # Approved!
            purpose="PhD Thesis Characterization",
        )
        decision = self.auditor.audit_booking(req)
        self.assertEqual(decision.status, "APPROVED")
        self.assertTrue(decision.is_approved)

    def test_automatic_memory_recording(self):
        """Scenario 10: Audit automatically logs record to memory."""
        req = BookingRequest(
            user_id="STU-001",
            equipment_id="EQ-101",
            start_time="2026-08-25 14:00",
            end_time="2026-08-25 15:00",
            duration_hours=1.0,
            request_text="Student requested 1h microscope slot",
        )
        self.auditor.audit_booking(req, record_to_memory=True)
        history = self.memory.get_user_history("STU-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].booking_result, "APPROVED")
        self.assertIn("microscope slot", history[0].request_text)


if __name__ == "__main__":
    unittest.main()
