"""Interactive Project 1 demonstration. Live LLM by default; simulation is opt-in."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", action="store_true", help="Use a labeled fake LLM; no provider calls")
    parser.add_argument("--scripted", action="store_true", help="TEST ONLY: script approval decisions in simulation")
    args = parser.parse_args()
    if args.scripted and not args.simulate:
        parser.error("--scripted is allowed only with --simulate. Live approvals must be interactive.")
    from dotenv import load_dotenv
    load_dotenv()
    if not args.simulate and not os.environ.get("GROQ_API_KEY"):
        parser.error("Configure GROQ_API_KEY in .env, or explicitly use --simulate for offline testing.")
    run_dir = Path(__file__).resolve().parent / "demo_runs" / str(uuid4())
    run_dir.mkdir(parents=True)
    from memory import long_term_db as db
    db.DB_PATH = str(run_dir / "memory.db")
    db.init_db()
    db.get_or_create_student("demo_learner", "Sample Learner")
    from agents import llm
    if args.simulate:
        from demo_support import SimulatedGroq
        os.environ["GROQ_API_KEY"] = "explicit-simulation-placeholder"
        llm.Groq = SimulatedGroq
        llm.get_client.cache_clear()
    from graph.workflow import build_workflow, request_state
    from langgraph.types import Command
    workflow = build_workflow()
    mode = "SIMULATED MODEL / SCRIPTED APPROVALS" if args.scripted else "SIMULATED MODEL / HUMAN APPROVALS" if args.simulate else "LIVE MODEL / HUMAN APPROVALS"
    print(f"\nMode: {mode}\nEach run uses a new database; previous runs are retained.\n")
    evidence = {"mode": mode, "cases": []}

    def run_case(name, thread, message, changes=None, scripted_decision=True):
        print(f"\nCASE: {name}\nThread: {thread}\nInput: {message}")
        config = {"configurable": {"thread_id": thread}}
        result = workflow.invoke(request_state("demo_learner", message, memory_changes=changes), config)
        print("Retrieved memory:", json.dumps(result["retrieved_memories"], indent=2))
        print("Response:\n", result["response"])
        before = db.get_memory_records("demo_learner")
        decision = None
        if result.get("__interrupt__"):
            print("Proposed action:", json.dumps(result["__interrupt__"][0].value, indent=2))
            if args.scripted:
                decision = scripted_decision
                print("TEST-ONLY scripted approval:", decision)
            else:
                while True:
                    choice = input("Approve this exact memory update? [y/n]: ").strip().lower()
                    if choice in {"y", "n"}:
                        decision = choice == "y"
                        break
                    print("Enter y or n.")
            result = workflow.invoke(Command(resume={"approved": decision}), config)
        after = db.get_memory_records("demo_learner")
        print("Steps:", " -> ".join(result["steps"]))
        print("Memory status:", result["memory_status"])
        evidence["cases"].append({"name": name, "thread_id": thread, "input": message,
                                  "retrieved_memory": result["retrieved_memories"],
                                  "response": result["response"], "steps": result["steps"],
                                  "approval": decision, "memory_before": before, "memory_after": after,
                                  "memory_status": result["memory_status"]})

    run_case("Baseline without useful memory", "baseline", "Explain Python loops", scripted_decision=False)
    run_case("Store two explicit preference records", "preferences", "Update my learning preferences.",
             {"preferred_style": "bullet_points", "level": "intermediate"})
    run_case("Normal request using permitted notes", "normal", "Explain Python loops")
    run_case("Later request in a different thread", "later", "Explain Python functions")
    run_case("Correct a saved preference", "correction", "Correct my preferred format.",
             {"preferred_style": "worked_examples"})
    run_case("Later request after correction", "after-correction", "Explain Python loops")
    print("\nFor the required rejection demonstration, enter n on the next approval prompt.")
    run_case("Reject a proposed change", "rejection", "Change my learning level.",
             {"level": "advanced"}, scripted_decision=False)
    rejection = evidence["cases"][-1]
    evidence["rejection_demonstrated"] = (rejection["approval"] is False and
                                         rejection["memory_before"] == rejection["memory_after"])
    path = run_dir / "evidence.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\nEvidence: {path}\nRejection demonstrated: {evidence['rejection_demonstrated']}")
    if args.simulate:
        print("This is simulation evidence, not proof of a working live LLM. Repeat without --simulate before submission.")


if __name__ == "__main__":
    main()
