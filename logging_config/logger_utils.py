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
from typing import List, Dict, Any, Optional
from pathlib import Path
from tabulate import tabulate  # pip install tabulate


class LogAnalyzer:
    """Analyze and display journey logs."""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
    
    def get_all_journeys(self) -> List[Dict[str, Any]]:
        """Get all journeys sorted by timestamp."""
        journeys = []
        requests_dir = os.path.join(self.logs_dir, "requests")
        
        if not os.path.exists(requests_dir):
            return []
        
        for file in os.listdir(requests_dir):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(requests_dir, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        journeys.append(data)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        
        return sorted(journeys, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def print_journey_summary(self, limit: int = 10):
        """Print summary of recent journeys."""
        journeys = self.get_all_journeys()[:limit]
        
        table_data = []
        for j in journeys:
            journey_id = j.get("journey_id", "N/A")
            query = j.get("user_query", "N/A")[:50]
            timestamp = j.get("timestamp", "N/A").split('T')[1][:8] if 'T' in j.get("timestamp", "") else "N/A"
            status = j.get("stages", {}).get("completion", [{}])[-1].get("status", "N/A") if j.get("stages", {}).get("completion") else "pending"
            
            table_data.append([journey_id.split('_')[1:3], query, timestamp, status])
        
        print("\n" + "="*100)
        print("RECENT JOURNEYS")
        print("="*100)
        print(tabulate(table_data, headers=["ID", "Query", "Time", "Status"], tablefmt="grid"))
        print()
    
    def print_journey_details(self, journey_id: str):
        """Print detailed information about a specific journey."""
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        
        if not os.path.exists(file_path):
            print(f"Journey {journey_id} not found")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            journey = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"JOURNEY DETAILS: {journey_id}")
        print(f"{'='*80}\n")
        
        print(f"Query: {journey.get('user_query')}")
        print(f"Started: {journey.get('timestamp')}")
        print(f"Last Updated: {journey.get('updated_at')}")
        print()
        
        stages = journey.get("stages", {})
        
        # Intent Detection
        if "intent_detection" in stages:
            intent_data = stages["intent_detection"][-1]
            print(f"📋 INTENT DETECTION")
            print(f"   Intent: {intent_data.get('intent')}")
            print(f"   Confidence: {intent_data.get('confidence')}")
            print(f"   Time: {intent_data.get('timestamp')}")
            print()
        
        # RAG Retrieval
        if "rag_retrieval" in stages:
            rag_data = stages["rag_retrieval"][-1]
            print(f"🔎 RAG RETRIEVAL")
            print(f"   Documents Retrieved: {rag_data.get('retrieved_docs_count')}")
            print(f"   Retrieval Time: {rag_data.get('retrieval_time_seconds'):.3f}s")
            print()
        
        # Action Plan
        if "action_plan" in stages:
            plan_data = stages["action_plan"][-1]
            plan = plan_data.get('action_plan', {})
            print(f"📝 ACTION PLAN")
            print(f"   Tool: {plan.get('tool')}")
            print(f"   Method: {plan.get('method')}")
            print(f"   Generation Time: {plan_data.get('generation_time_seconds'):.3f}s")
            print(f"   Full Plan:")
            print(json.dumps(plan, indent=6))
            print()
        
        # Tool Execution
        if "tool_execution" in stages:
            for tool_exec in stages["tool_execution"]:
                if tool_exec.get("status") == "in_progress":
                    print(f"🔧 TOOL EXECUTION STARTED")
                    print(f"   Tool: {tool_exec.get('tool_name')}")
                    print()
                elif "execution_time_seconds" in tool_exec:
                    print(f"🎯 TOOL EXECUTION RESULT")
                    print(f"   Tool: {tool_exec.get('tool_name')}")
                    print(f"   Success: {tool_exec.get('success')}")
                    print(f"   Time: {tool_exec.get('execution_time_seconds'):.3f}s")
                    if tool_exec.get('error'):
                        print(f"   Error: {tool_exec.get('error')}")
                    print()
        
        # Completion
        if "completion" in stages:
            completion = stages["completion"][-1]
            print(f"✨ COMPLETION")
            print(f"   Status: {completion.get('status')}")
            print(f"   Total Time: {completion.get('total_time_seconds'):.3f}s" if completion.get('total_time_seconds') else "")
            print()
        
        # Errors
        if "error" in stages:
            for error in stages["error"]:
                print(f"⚠️  ERROR")
                print(f"   Type: {error.get('error_type')}")
                print(f"   Stage: {error.get('stage')}")
                print(f"   Message: {error.get('error_message')}")
                print()
        
        print(f"{'='*80}\n")
    
    def get_journey_timeline(self, journey_id: str) -> List[Dict[str, Any]]:
        """Get a timeline of all events in a journey."""
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            journey = json.load(f)
        
        timeline = []
        stages = journey.get("stages", {})
        
        for stage_name, events in stages.items():
            for event in events if isinstance(events, list) else [events]:
                timeline.append({
                    "stage": stage_name,
                    "timestamp": event.get("timestamp"),
                    "details": event
                })
        
        return sorted(timeline, key=lambda x: x.get("timestamp", ""))
    
    def calculate_stage_durations(self, journey_id: str) -> Dict[str, float]:
        """Calculate duration of each stage."""
        timeline = self.get_journey_timeline(journey_id)
        
        if not timeline:
            return {}
        
        durations = {}
        stage_start_times = {}
        
        for event in timeline:
            stage = event.get("stage")
            timestamp = event.get("timestamp")
            
            if stage not in stage_start_times:
                stage_start_times[stage] = timestamp
        
        # Calculate total time
        if len(timeline) > 0:
            start_time = datetime.fromisoformat(timeline[0].get("timestamp"))
            end_time = datetime.fromisoformat(timeline[-1].get("timestamp"))
            durations["total"] = (end_time - start_time).total_seconds()
        
        return durations
    
    def export_journey_csv(self, journey_id: str, output_file: str = None):
        """Export journey events to CSV format."""
        import csv
        
        timeline = self.get_journey_timeline(journey_id)
        
        if not timeline:
            print(f"No journey found with ID {journey_id}")
            return
        
        if output_file is None:
            output_file = f"journey_{journey_id}_export.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Stage", "Timestamp", "Details"])
            
            for event in timeline:
                writer.writerow([
                    event.get("stage"),
                    event.get("timestamp"),
                    json.dumps(event.get("details"), indent=2)
                ])
        
        print(f"Journey exported to {output_file}")
    
    def search_journeys(self, query_text: str) -> List[Dict[str, Any]]:
        """Search journeys by query text."""
        journeys = self.get_all_journeys()
        results = []
        
        query_lower = query_text.lower()
        for journey in journeys:
            if query_lower in journey.get("user_query", "").lower():
                results.append(journey)
        
        return results
    
    def get_journey_errors(self, journey_id: str) -> List[Dict[str, Any]]:
        """Get all errors from a specific journey."""
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            journey = json.load(f)
        
        stages = journey.get("stages", {})
        errors = stages.get("error", [])
        
        return errors if isinstance(errors, list) else [errors]
    
    def print_error_report(self, journey_id: str):
        """Print detailed error report for a journey."""
        errors = self.get_journey_errors(journey_id)
        
        if not errors:
            print(f"No errors found in journey {journey_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"ERROR REPORT: {journey_id}")
        print(f"{'='*80}\n")
        
        for i, error in enumerate(errors, 1):
            print(f"Error #{i}")
            print(f"  Type: {error.get('error_type')}")
            print(f"  Stage: {error.get('stage')}")
            print(f"  Message: {error.get('error_message')}")
            print(f"  Time: {error.get('timestamp')}")
            if error.get('stack_trace'):
                print(f"  Stack Trace:")
                for line in error.get('stack_trace').split('\n'):
                    print(f"    {line}")
            print()


# CLI Commands for easy access
def main():
    """Simple CLI for log analysis."""
    import sys
    
    analyzer = LogAnalyzer()
    
    if len(sys.argv) < 2:
        print("Usage: python logger_utils.py <command> [args]")
        print("\nCommands:")
        print("  list                    - List recent journeys")
        print("  show <journey_id>       - Show journey details")
        print("  search <query_text>     - Search journeys by query text")
        print("  errors <journey_id>     - Show errors for journey")
        print("  export <journey_id>     - Export journey to CSV")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        analyzer.print_journey_summary(limit)
    
    elif command == "show" and len(sys.argv) > 2:
        analyzer.print_journey_details(sys.argv[2])
    
    elif command == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = analyzer.search_journeys(query)
        print(f"\nFound {len(results)} journeys matching '{query}':\n")
        for journey in results:
            print(f"  {journey.get('journey_id')}: {journey.get('user_query')}")
    
    elif command == "errors" and len(sys.argv) > 2:
        analyzer.print_error_report(sys.argv[2])
    
    elif command == "export" and len(sys.argv) > 2:
        output = sys.argv[3] if len(sys.argv) > 3 else None
        analyzer.export_journey_csv(sys.argv[2], output)
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
