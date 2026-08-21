"""Interactive CLI for Smart Laboratory Resource Agent.

Run this script to test your own natural language lab resource requests in real time!
"""

import os
from agents import LabOrchestrator


def main():
    print("=" * 65)
    print("🔬 SMART LABORATORY RESOURCE AGENT - INTERACTIVE CLI 🤖")
    print("=" * 65)
    print("Features supported:")
    print("  • Natural-language equipment booking")
    print("  • Inventory availability checks")
    print("  • Conflict detection & alternative slot recommendation")
    print("  • Auditor compliance (operating hours: 08:00-20:00, max 4 hours)")
    print("  • Automated re-planning loop")
    print("=" * 65)
    print("Type 'exit' or 'quit' to close.\n")

    # If user has an OpenAI API key, they can set it in environment or it uses heuristic parser
    orchestrator = LabOrchestrator()

    while True:
        try:
            prompt = input("\n📝 Enter lab request > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            print("\n🔄 Processing multi-agent workflow...")
            response = orchestrator.process_request(prompt)

            print("\n" + "-" * 50)
            print(f"📊 Status   : {response.status}")
            print(f"💬 Summary  : {response.summary_message}")

            if response.final_booking:
                fb = response.final_booking
                print("\n✅ Confirmed Booking Details:")
                print(f"   • Equipment : {fb.equipment_name} ({fb.equipment_id})")
                print(f"   • Location  : {fb.location}")
                print(f"   • Date      : {fb.date}")
                print(f"   • Time Slot : {fb.start_time} - {fb.end_time}")
                print(f"   • Purpose   : {fb.purpose}")
                print(f"   • Researcher: {fb.researcher}")

            if response.replan_count > 0:
                print(f"\n🔁 Re-planning History ({response.replan_count} iterations):")
                for entry in response.replan_history:
                    print(f"   [Re-plan #{entry.iteration}] Reason: {entry.trigger_reason}")
                    print(f"                   Adjustment: {entry.adjusted_parameters}")

            print("\n🔍 Multi-Agent Execution Trace:")
            for trace_line in response.execution_trace:
                print(f"   {trace_line}")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
