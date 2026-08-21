# Smart Laboratory Resource Agent 🔬🤖

An autonomous AI-driven Laboratory Resource Management System built for the Agentic AI Hackathon.

The system uses multi-agent collaboration, backend tools, RAG-based laboratory policies, interaction memory, conflict resolution, scheduling, and safety/compliance auditing to manage laboratory equipment booking requests.

Built with Python, OpenAI, LangChain, FastAPI, RAG, and simulated laboratory data.

---

## Project Structure

```text
smart-lab-agent/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── inventory_agent.py
│   ├── scheduling_agent.py
│   ├── conflict_agent.py
│   └── auditor_agent.py
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   └── api/
│       ├── __init__.py
│       ├── inventory.py
│       └── booking.py
│
├── tools/
│   ├── __init__.py
│   ├── inventory_tools.py
│   ├── booking_tools.py
│   └── scheduling_tools.py
│
├── rag/
│   ├── __init__.py
│   ├── lab_rules.txt
│   ├── equipment_rules.txt
│   ├── booking_policy.txt
│   └── rag_pipeline.py
│
├── memory/
│   ├── __init__.py
│   └── memory.py
│
├── auditor/
│   ├── __init__.py
│   └── auditor_support.py
│
├── data/
│   ├── __init__.py
│   ├── equipment.json
│   ├── bookings.json
│   └── dummy_inventory.py
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_tools.py
│   ├── test_member4.py
│   └── test_oscilloscope_booking.py
│
├── main.py
├── demo.py
├── requirements.txt
└── README.md