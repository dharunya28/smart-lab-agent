"""Orchestrator Agent for Smart Laboratory Resource Agent.

Coordinates multi-agent workflow:
1. Natural-language request understanding (equipment, date, time, duration, purpose).
2. Inventory verification via InventoryAgent.
3. Schedule verification via SchedulingAgent.
4. Conflict resolution via ConflictResolverAgent.
5. Compliance auditing via AuditorAgent.
6. Automated Re-planning loop if Auditor rejects a proposed reservation.
"""

from typing import Dict, List, Optional, Any
import os
import re
import json
from datetime import datetime, date
from pydantic import BaseModel, Field

# LangChain / OpenAI imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .inventory_agent import InventoryAgent, InventoryCheckResult
from .scheduling_agent import SchedulingAgent, ScheduleCheckResult
from .conflict_agent import ConflictResolverAgent, ConflictDecision
from .auditor_agent import AuditorAgent, AuditResult


class ParsedLabRequest(BaseModel):
    """Structured representation of extracted lab resource request."""
    equipment_name: str
    date: str  # "YYYY-MM-DD"
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    duration_hours: float
    purpose: str
    researcher: str = "Lab Researcher"


class FinalBookingRecord(BaseModel):
    """Details of the finalized lab booking."""
    equipment_id: str
    equipment_name: str
    location: str
    date: str
    start_time: str
    end_time: str
    purpose: str
    researcher: str
    status: str  # "CONFIRMED"


class ReplanLogEntry(BaseModel):
    """Record of a re-planning step."""
    iteration: int
    trigger_reason: str
    adjusted_parameters: Dict[str, Any]
    outcome: str


class OrchestratorResponse(BaseModel):
    """Comprehensive structured result returned by the Orchestrator."""
    status: str  # "CONFIRMED", "CONFIRMED_WITH_REPLAN", "CONFIRMED_ALTERNATIVE", "REJECTED"
    summary_message: str
    request_parsed: Optional[ParsedLabRequest] = None
    final_booking: Optional[FinalBookingRecord] = None
    inventory_status: Optional[InventoryCheckResult] = None
    schedule_status: Optional[ScheduleCheckResult] = None
    conflict_decision: Optional[ConflictDecision] = None
    audit_result: Optional[AuditResult] = None
    replan_count: int = 0
    replan_history: List[ReplanLogEntry] = Field(default_factory=list)
    execution_trace: List[str] = Field(default_factory=list)


class LabOrchestrator:
    """Master orchestrator agent coordinating laboratory resource reservation."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        inventory_agent: Optional[InventoryAgent] = None,
        scheduling_agent: Optional[SchedulingAgent] = None,
        conflict_agent: Optional[ConflictResolverAgent] = None,
        auditor_agent: Optional[AuditorAgent] = None,
        max_replan_attempts: int = 3
    ):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.max_replan_attempts = max_replan_attempts

        # Sub-agents
        self.inventory_agent = inventory_agent or InventoryAgent()
        self.scheduling_agent = scheduling_agent or SchedulingAgent()
        self.conflict_agent = conflict_agent or ConflictResolverAgent()
        self.auditor_agent = auditor_agent or AuditorAgent()

        # Initialize LLM if available and API key configured
        self.llm = None
        if LANGCHAIN_AVAILABLE and self.api_key:
            try:
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=self.api_key,
                    temperature=0.0
                )
            except Exception:
                self.llm = None

    def _parse_natural_language_request(self, user_prompt: str) -> ParsedLabRequest:
        """Parse natural-language request into structured parameters using LLM with regex fallback."""
        if self.llm:
            try:
                system_prompt = (
                    "You are a laboratory natural language parser. "
                    "Extract the following fields from the user request as a valid JSON object:\n"
                    "- equipment_name (string, e.g. 'Confocal Microscope', 'PCR', 'HPLC')\n"
                    "- date (string in YYYY-MM-DD format. If relative or omitted, use '2026-08-25')\n"
                    "- start_time (string in HH:MM 24-hour format, e.g. '10:00')\n"
                    "- end_time (string in HH:MM 24-hour format, e.g. '12:00')\n"
                    "- duration_hours (float, duration in hours)\n"
                    "- purpose (string, scientific/experiment purpose)\n"
                    "- researcher (string, name of researcher or 'Researcher')\n"
                    "Output ONLY the JSON object, no other text or markdown code fences."
                )
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = self.llm.invoke(messages)
                content = response.content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                data = json.loads(content)
                return ParsedLabRequest(**data)
            except Exception:
                pass  # Fallback to rule-based parser

        # Robust Rule-Based Parser Fallback
        return self._rule_based_parse(user_prompt)

    def _rule_based_parse(self, prompt: str) -> ParsedLabRequest:
        """Heuristic rule-based parser for laboratory booking requests."""
        prompt_lower = prompt.lower()

        # 1. Identify Equipment
        eq_name = "Confocal Microscope"
        if "pcr" in prompt_lower or "thermocycler" in prompt_lower:
            eq_name = "PCR Thermocycler"
        elif "hplc" in prompt_lower or "chromatograph" in prompt_lower:
            eq_name = "HPLC System"
        elif "centrifuge" in prompt_lower:
            eq_name = "Microcentrifuge"
        elif "flow cytometer" in prompt_lower or "facs" in prompt_lower:
            eq_name = "Flow Cytometer"
        elif "spectrophotometer" in prompt_lower or "nanodrop" in prompt_lower:
            eq_name = "UV-Vis Spectrophotometer"
        elif "autoclave" in prompt_lower:
            eq_name = "Autoclave Sterilizer"
        elif "confocal" in prompt_lower or "microscope" in prompt_lower:
            eq_name = "Confocal Microscope"

        # 2. Extract Date (YYYY-MM-DD or default)
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", prompt)
        req_date = date_match.group(1) if date_match else "2026-08-25"

        # 3. Extract Times (e.g. 10:00 to 12:00, 10am to 12pm, 10:00 - 16:00)
        time_matches = re.findall(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", prompt_lower)
        start_time = "10:00"
        end_time = "12:00"

        # Look for explicit HH:MM patterns
        hhmm = re.findall(r"\b(\d{1,2}:\d{2})\b", prompt)
        if len(hhmm) >= 2:
            start_time = hhmm[0].zfill(5)
            end_time = hhmm[1].zfill(5)
        elif len(hhmm) == 1:
            start_time = hhmm[0].zfill(5)
            # Default to +2 hours
            s_h, s_m = map(int, start_time.split(":"))
            end_time = f"{min(23, s_h + 2):02d}:{s_m:02d}"

        # Look for explicit duration keywords (e.g. "for 5 hours", "for 6 hours", "3 hours")
        dur_match = re.search(r"for\s+(\d+(?:\.\d+)?)\s*hours?", prompt_lower)
        if dur_match:
            duration_val = float(dur_match.group(1))
            s_h, s_m = map(int, start_time.split(":"))
            e_h = s_h + int(duration_val)
            e_m = s_m + int((duration_val - int(duration_val)) * 60)
            end_time = f"{min(23, e_h):02d}:{e_m:02d}"

        # Calculate duration in hours
        try:
            sh, sm = map(int, start_time.split(":"))
            eh, em = map(int, end_time.split(":"))
            duration_hours = max(0.5, ((eh * 60 + em) - (sh * 60 + sm)) / 60.0)
        except Exception:
            duration_hours = 2.0

        # 4. Extract Purpose
        purpose = "Standard experimental analysis"
        for kw in ["for ", "purpose: ", "to "]:
            if kw in prompt_lower:
                part = prompt[prompt_lower.index(kw) + len(kw):].strip()
                if len(part) > 5:
                    purpose = part
                    break

        # 5. Extract Researcher
        researcher = "Lab Researcher"
        res_match = re.search(r"(?:dr\.|prof\.|researcher)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", prompt, re.IGNORECASE)
        if res_match:
            researcher = res_match.group(0).strip()

        return ParsedLabRequest(
            equipment_name=eq_name,
            date=req_date,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            purpose=purpose,
            researcher=researcher
        )

    def process_request(self, user_prompt: str) -> OrchestratorResponse:
        """Execute end-to-end multi-agent orchestration for a laboratory resource request."""
        trace: List[str] = []
        replan_history: List[ReplanLogEntry] = []

        trace.append(f"[Orchestrator] Received natural-language request: '{user_prompt}'")

        # Step 1: Parse request
        parsed = self._parse_natural_language_request(user_prompt)
        trace.append(
            f"[Orchestrator] Parsed request: Equipment='{parsed.equipment_name}', "
            f"Date='{parsed.date}', Window={parsed.start_time}-{parsed.end_time} ({parsed.duration_hours}h), "
            f"Purpose='{parsed.purpose}', Researcher='{parsed.researcher}'"
        )

        # Step 2: Inventory Agent Check
        trace.append(f"[InventoryAgent] Querying availability for '{parsed.equipment_name}'...")
        inventory_result = self.inventory_agent.check_availability(parsed.equipment_name)
        trace.append(f"[InventoryAgent] Result: {inventory_result.message}")

        if not inventory_result.found or not inventory_result.available:
            trace.append("[Orchestrator] Equipment unavailable. Terminating request with structured failure.")
            return OrchestratorResponse(
                status="EQUIPMENT_UNAVAILABLE",
                summary_message=inventory_result.message,
                request_parsed=parsed,
                inventory_status=inventory_result,
                execution_trace=trace
            )

        equipment_id = inventory_result.equipment_id
        equipment_name = inventory_result.name
        location = inventory_result.location

        # Working variables for scheduling and re-planning
        current_date = parsed.date
        current_start = parsed.start_time
        current_end = parsed.end_time
        current_purpose = parsed.purpose

        replan_iteration = 0
        final_booking = None
        audit_result = None
        conflict_decision = None
        schedule_result = None

        while replan_iteration <= self.max_replan_attempts:
            # Step 3: Scheduling Agent Check
            trace.append(
                f"[SchedulingAgent] (Attempt {replan_iteration + 1}) Checking slot {current_start}-{current_end} "
                f"on {current_date} for {equipment_id}..."
            )
            schedule_result = self.scheduling_agent.check_schedule(
                equipment_id=equipment_id,
                date=current_date,
                start_time=current_start,
                end_time=current_end
            )
            trace.append(f"[SchedulingAgent] Result: {schedule_result.message}")

            # Step 4: Conflict Resolver Agent
            trace.append(f"[ConflictResolverAgent] Evaluating booking conflicts and available alternatives...")
            conflict_decision = self.conflict_agent.resolve(
                equipment_id=equipment_id,
                equipment_name=equipment_name,
                date=current_date,
                requested_start=current_start,
                requested_end=current_end,
                is_slot_free=schedule_result.is_available,
                conflicting_bookings=schedule_result.conflicting_bookings,
                available_slots=schedule_result.available_slots
            )
            trace.append(f"[ConflictResolverAgent] Decision: {conflict_decision.explanation}")

            if conflict_decision.decision == "NO_SLOT_AVAILABLE":
                trace.append("[Orchestrator] No slots available on requested date. Terminating with REJECTED.")
                return OrchestratorResponse(
                    status="REJECTED",
                    summary_message=f"No available slots for {equipment_name} on {current_date}.",
                    request_parsed=parsed,
                    inventory_status=inventory_result,
                    schedule_status=schedule_result,
                    conflict_decision=conflict_decision,
                    replan_count=replan_iteration,
                    replan_history=replan_history,
                    execution_trace=trace
                )

            # Target slot after conflict resolution
            proposed_slot = conflict_decision.recommended_slot or {
                "start_time": current_start,
                "end_time": current_end
            }

            # Step 5: Auditor Agent Verification
            trace.append(
                f"[AuditorAgent] Auditing proposed booking for {equipment_name} "
                f"({current_date} {proposed_slot['start_time']}-{proposed_slot['end_time']})..."
            )
            audit_result = self.auditor_agent.audit_booking(
                equipment_id=equipment_id,
                equipment_name=equipment_name,
                equipment_status=inventory_result.status,
                date=current_date,
                start_time=proposed_slot["start_time"],
                end_time=proposed_slot["end_time"],
                purpose=current_purpose,
                researcher=parsed.researcher
            )
            trace.append(f"[AuditorAgent] Audit Status: {audit_result.status} | Reason: {audit_result.reason}")

            # If Auditor APPROVES -> Success!
            if audit_result.approved:
                final_booking = FinalBookingRecord(
                    equipment_id=equipment_id,
                    equipment_name=equipment_name,
                    location=location,
                    date=current_date,
                    start_time=proposed_slot["start_time"],
                    end_time=proposed_slot["end_time"],
                    purpose=current_purpose,
                    researcher=parsed.researcher,
                    status="CONFIRMED"
                )
                break

            # Step 6: Auditor REJECTS -> Automated Re-Planning
            replan_iteration += 1
            trace.append(
                f"[Orchestrator] Booking rejected by Auditor. Initiating Re-plan #{replan_iteration}..."
            )

            if replan_iteration > self.max_replan_attempts:
                trace.append(f"[Orchestrator] Exceeded maximum replan limit ({self.max_replan_attempts}).")
                break

            # Analyze violations and adjust parameters
            adjusted_params = {}
            new_start = proposed_slot["start_time"]
            new_end = proposed_slot["end_time"]

            # Fix 1: Max duration violation (> 4 hours)
            if not audit_result.audit_checks.get("within_max_duration", True):
                sh, sm = map(int, new_start.split(":"))
                # Cap to max 4 hours
                max_end_h = sh + int(self.auditor_agent.max_duration_hours)
                new_end = f"{min(20, max_end_h):02d}:{sm:02d}"
                adjusted_params["adjusted_duration_to_max"] = f"{new_start} - {new_end}"
                trace.append(f"[Orchestrator Re-plan] Capped duration to policy max (4h): {new_start} - {new_end}")

            # Fix 2: Operating hours violation (< 08:00 or > 20:00)
            if not audit_result.audit_checks.get("within_operating_hours", True):
                sh, sm = map(int, new_start.split(":"))
                if sh < self.auditor_agent.lab_open_hour:
                    new_start = f"{self.auditor_agent.lab_open_hour:02d}:00"
                    new_end = f"{self.auditor_agent.lab_open_hour + 2:02d}:00"
                elif sh >= self.auditor_agent.lab_close_hour:
                    new_start = f"{self.auditor_agent.lab_close_hour - 2:02d}:00"
                    new_end = f"{self.auditor_agent.lab_close_hour:02d}:00"
                adjusted_params["adjusted_to_operating_hours"] = f"{new_start} - {new_end}"
                trace.append(f"[Orchestrator Re-plan] Shifted to lab operating hours: {new_start} - {new_end}")

            # Update current window for next iteration
            current_start = new_start
            current_end = new_end

            replan_history.append(ReplanLogEntry(
                iteration=replan_iteration,
                trigger_reason=audit_result.reason,
                adjusted_parameters=adjusted_params,
                outcome=f"Adjusted proposed window to {current_start}-{current_end} and re-evaluating."
            ))

        # Formulate final status
        if final_booking:
            if replan_iteration > 0:
                final_status = "CONFIRMED_WITH_REPLAN"
                summary_msg = (
                    f"Booking APPROVED after {replan_iteration} re-plan adjustment(s). "
                    f"Reserved {final_booking.equipment_name} in {final_booking.location} "
                    f"on {final_booking.date} from {final_booking.start_time} to {final_booking.end_time}."
                )
            elif conflict_decision and conflict_decision.has_conflict:
                final_status = "CONFIRMED_ALTERNATIVE"
                summary_msg = (
                    f"Booking APPROVED on alternative slot due to schedule conflict. "
                    f"Reserved {final_booking.equipment_name} on {final_booking.date} "
                    f"from {final_booking.start_time} to {final_booking.end_time}."
                )
            else:
                final_status = "CONFIRMED"
                summary_msg = (
                    f"Booking APPROVED. Reserved {final_booking.equipment_name} in {final_booking.location} "
                    f"on {final_booking.date} from {final_booking.start_time} to {final_booking.end_time}."
                )
        else:
            final_status = "REJECTED"
            summary_msg = (
                f"Booking REJECTED. Auditor audit could not be satisfied after {replan_iteration} replan attempt(s): "
                f"{audit_result.reason if audit_result else 'Unknown error'}"
            )

        trace.append(f"[Orchestrator] Final Status: {final_status} | {summary_msg}")

        return OrchestratorResponse(
            status=final_status,
            summary_message=summary_msg,
            request_parsed=parsed,
            final_booking=final_booking,
            inventory_status=inventory_result,
            schedule_status=schedule_result,
            conflict_decision=conflict_decision,
            audit_result=audit_result,
            replan_count=replan_iteration,
            replan_history=replan_history,
            execution_trace=trace
        )
