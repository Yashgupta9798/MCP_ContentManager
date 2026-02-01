"""
Logger Utilities - Tools for analyzing and viewing journey logs

This module provides utilities to:
1. View journey logs in different formats
2. Analyze journey timings
3. Export logs for analysis
4. Search through logs
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from tabulate import tabulate  # pip install tabulate


def derive_tool_from_plan(plan: Dict[str, Any]) -> str:
    """Derive tool name from operation + method."""
    operation = plan.get("operation")
    method = plan.get("method")

    if operation == "SEARCH" and method == "GET":
        return "search_records"
    if operation == "CREATE" and method == "POST":
        return "create_record"

    return "unknown"


class LogAnalyzer:
    """Analyze and display journey logs."""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir

    def get_all_journeys(self) -> List[Dict[str, Any]]:
        journeys = []
        requests_dir = os.path.join(self.logs_dir, "requests")

        if not os.path.exists(requests_dir):
            return []

        for file in os.listdir(requests_dir):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(requests_dir, file), "r", encoding="utf-8") as f:
                        journeys.append(json.load(f))
                except Exception as e:
                    print(f"Error reading {file}: {e}")

        return sorted(journeys, key=lambda x: x.get("timestamp", ""), reverse=True)

    def print_journey_summary(self, limit: int = 10):
        journeys = self.get_all_journeys()[:limit]
        table_data = []

        for j in journeys:
            journey_id = j.get("journey_id", "N/A")
            query = (j.get("user_query") or "N/A")[:50]
            timestamp = j.get("timestamp", "N/A")
            time_only = timestamp.split("T")[1][:8] if "T" in timestamp else "N/A"

            completion = j.get("stages", {}).get("completion", [])
            status = completion[-1].get("success") if completion else "pending"

            table_data.append([
                journey_id,
                query,
                time_only,
                status
            ])

        print("\n" + "=" * 100)
        print("RECENT JOURNEYS")
        print("=" * 100)
        print(tabulate(table_data, headers=["Journey ID", "Query", "Time", "Status"], tablefmt="grid"))
        print()

    def print_journey_details(self, journey_id: str):
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")

        if not os.path.exists(file_path):
            print(f"Journey {journey_id} not found")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            journey = json.load(f)

        print(f"\n{'=' * 80}")
        print(f"JOURNEY DETAILS: {journey_id}")
        print(f"{'=' * 80}\n")

        print(f"Query: {journey.get('user_query')}")
        print(f"Started: {journey.get('timestamp')}")
        print(f"Last Updated: {journey.get('updated_at')}")
        print()

        stages = journey.get("stages", {})

        if "intent_detection" in stages:
            intent = stages["intent_detection"][-1]
            print("📋 INTENT DETECTION")
            print(f"   Intent: {intent.get('intent')}")
            print(f"   Confidence: {intent.get('confidence')}")
            print()

        if "rag_retrieval" in stages:
            rag = stages["rag_retrieval"][-1]
            print("🔎 RAG RETRIEVAL")
            print(f"   Docs: {len(rag.get('retrieved_docs', []))}")
            print(f"   Time: {rag.get('retrieval_time'):.3f}s")
            print()

        if "action_plan" in stages:
            plan_data = stages["action_plan"][-1]
            plan = plan_data.get("action_plan", {})
            tool = derive_tool_from_plan(plan)

            print("📝 ACTION PLAN")
            print(f"   Operation: {plan.get('operation')}")
            print(f"   Method: {plan.get('method')}")
            print(f"   Derived Tool: {tool}")
            print("   Full Plan:")
            print(json.dumps(plan, indent=4))
            print()

        if "tool_execution" in stages:
            for step in stages["tool_execution"]:
                if step.get("status") == "started":
                    print("🔧 TOOL EXECUTION STARTED")
                    print(f"   Tool: {step.get('tool')}")
                else:
                    print("🎯 TOOL EXECUTION RESULT")
                    print(f"   Tool: {step.get('tool')}")
                    print(f"   Success: {step.get('success')}")
                    print(f"   Time: {step.get('execution_time')}")
                    if step.get("error"):
                        print(f"   Error: {step.get('error')}")
                print()

        if "completion" in stages:
            comp = stages["completion"][-1]
            print("✨ COMPLETION")
            print(f"   Success: {comp.get('success')}")
            print(f"   Total Time: {comp.get('total_time')}")
            print()

        if "error" in stages:
            for err in stages["error"]:
                print("⚠️ ERROR")
                print(f"   Type: {err.get('error_type')}")
                print(f"   Stage: {err.get('stage')}")
                print(f"   Message: {err.get('error_message')}")
                print()

        print(f"{'=' * 80}\n")

    def get_journey_timeline(self, journey_id: str) -> List[Dict[str, Any]]:
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        if not os.path.exists(file_path):
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            journey = json.load(f)

        timeline = []
        for stage, events in journey.get("stages", {}).items():
            for e in events:
                timeline.append({
                    "stage": stage,
                    "timestamp": e.get("timestamp"),
                    "details": e
                })

        return sorted(timeline, key=lambda x: x["timestamp"])

    def calculate_stage_durations(self, journey_id: str) -> Dict[str, float]:
        timeline = self.get_journey_timeline(journey_id)
        if not timeline:
            return {}

        start = datetime.fromisoformat(timeline[0]["timestamp"])
        end = datetime.fromisoformat(timeline[-1]["timestamp"])
        return {"total": (end - start).total_seconds()}


def main():
    import sys
    analyzer = LogAnalyzer()

    if len(sys.argv) < 2:
        print("Usage: python logger_utils.py <list|show|search|errors|export>")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        analyzer.print_journey_summary()
    elif cmd == "show" and len(sys.argv) > 2:
        analyzer.print_journey_details(sys.argv[2])
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
