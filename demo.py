"""Demo and verification script for Smart Laboratory Resource Agent.

Demonstrates all key multi-agent scenarios:
1. Standard clean booking
2. Schedule conflict detection & automatic resolution
3. Auditor policy violation with automated Orchestrator re-planning
4. Equipment in maintenance / unavailable
"""

import json
from agents import LabOrchestrator


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"  SCENARIO: {title}")
    print("=" * 70)


def print_response(response):
    print(f"\n>>> FINAL STATUS: {response.status}")
    print(f">>> SUMMARY: {response.summary_message}")

    if response.final_booking:
        print("\n--- Final Confirmed Booking ---")
        print(f"  Equipment : {response.final_booking.equipment_name} ({response.final_booking.equipment_id})")
        print(f"  Location  : {response.final_booking.location}")
        print(f"  Date      : {response.final_booking.date}")
        print(f"  Time Slot : {response.final_booking.start_time} - {response.final_booking.end_time}")
        print(f"  Purpose   : {response.final_booking.purpose}")
        print(f"  Researcher: {response.final_booking.researcher}")

    if response.replan_count > 0:
        print(f"\n--- Re-planning Iterations ({response.replan_count}) ---")
        for log in response.replan_history:
            print(f"  [Iteration {log.iteration}] Reason : {log.trigger_reason}")
            print(f"                     Action : {log.adjusted_parameters}")
            print(f"                     Outcome: {log.outcome}")

    print("\n--- Multi-Agent Execution Trace ---")
    for step in response.execution_trace:
        print(f"  {step}")


def main():
    orchestrator = LabOrchestrator()

    # Scenario 1: Standard clean booking
    print_separator("1. Direct Available Booking")
    prompt_1 = "Book the Centrifuge 5424R on 2026-08-25 from 11:00 to 13:00 for bacterial pellet harvesting Dr. Miller"
    res_1 = orchestrator.process_request(prompt_1)
    print_response(res_1)
    assert res_1.status == "CONFIRMED"
    assert res_1.final_booking is not None

    # Scenario 2: Schedule conflict -> Conflict Resolver finds alternative slot
    print_separator("2. Schedule Conflict Resolution")
    prompt_2 = "I need the Confocal Microscope on 2026-08-25 from 10:00 to 12:00 for live cell fluorescence imaging"
    res_2 = orchestrator.process_request(prompt_2)
    print_response(res_2)
    assert res_2.status == "CONFIRMED_ALTERNATIVE"
    assert res_2.conflict_decision.has_conflict is True
    assert res_2.final_booking is not None

    # Scenario 3: Policy violation (6 hours > 4 hours limit) -> Auditor Rejection & Orchestrator Re-planning
    print_separator("3. Auditor Policy Violation & Automated Orchestrator Re-Planning")
    prompt_3 = "Book the PCR Thermocycler on 2026-08-25 from 12:00 to 18:00 (for 6 hours) for continuous gene amplification Dr. Evans"
    res_3 = orchestrator.process_request(prompt_3)
    print_response(res_3)
    assert res_3.status == "CONFIRMED_WITH_REPLAN"
    assert res_3.replan_count > 0
    assert res_3.final_booking is not None

    # Scenario 4: Equipment under maintenance
    print_separator("4. Equipment Under Maintenance")
    prompt_4 = "Please reserve the HPLC System on 2026-08-25 from 09:00 to 11:00 for protein chromatography"
    res_4 = orchestrator.process_request(prompt_4)
    print_response(res_4)
    assert res_4.status == "EQUIPMENT_UNAVAILABLE"
    assert res_4.final_booking is None

    print("\n" + "=" * 70)
    print("  ALL 4 SCENARIOS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
