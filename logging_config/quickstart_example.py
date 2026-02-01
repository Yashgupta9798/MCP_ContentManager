"""
Quick Start Example - Using the Journey Logger

This file demonstrates how to quickly implement journey logging in your system.

RUN THIS EXAMPLE:
    python logging_config/quickstart_example.py
"""

import json
import time
from logging_config.journey_logger import get_journey_logger
from logging_config.logger_utils import LogAnalyzer


def example_journey_simulation():
    """
    Simulate a complete query journey to demonstrate logging.
    """
    
    print("\n" + "="*80)
    print("JOURNEY LOGGER - QUICK START EXAMPLE")
    print("="*80 + "\n")
    
    # Initialize logger
    logger = get_journey_logger()
    
    # Simulate a user query
    user_query = "Show me all active leave policies for Q1 2026"
    
    # START JOURNEY
    journey_id = logger.start_journey(user_query)
    
    time.sleep(0.5)  # Simulate time
    
    # STAGE 1: Intent Detection
    print("\n⏳ Simulating intent detection...")
    time.sleep(1)
    
    detected_intent = "SEARCH"
    logger.log_intent_detection(
        journey_id=journey_id,
        intent=detected_intent,
        confidence=0.95
    )
    
    time.sleep(0.5)
    
    # STAGE 2: RAG Retrieval
    print("\n⏳ Simulating RAG document retrieval...")
    retrieved_docs = [
        "Leave_Policy_Q1_2026.pdf",
        "HR_Guidelines_Active.md",
        "Employee_Benefits.txt"
    ]
    
    logger.log_rag_retrieval(
        journey_id=journey_id,
        query=user_query,
        retrieved_docs=retrieved_docs,
        retrieval_time=0.834
    )
    
    time.sleep(0.5)
    
    # STAGE 3: Action Plan Generation
    print("\n⏳ Generating action plan...")
    
    action_plan = {
        "tool": "search",
        "method": "GET",
        "operation": "search_records",
        "filters": {
            "type": "leave_policy",
            "status": "active",
            "quarter": "Q1",
            "year": 2026
        },
        "sort": "modified_date",
        "order": "desc"
    }
    
    logger.log_action_plan(
        journey_id=journey_id,
        action_plan=action_plan,
        generation_time=1.234
    )
    
    time.sleep(0.5)
    
    # STAGE 4: Tool Execution
    print("\n⏳ Executing search tool...")
    
    logger.log_tool_execution_start(
        journey_id=journey_id,
        tool_name="search_records",
        arguments={"action_plan": action_plan}
    )
    
    time.sleep(1.5)  # Simulate tool execution
    
    # Tool Result
    search_results = {
        "status": "success",
        "records_found": 3,
        "records": [
            {
                "id": "REC-001",
                "title": "Q1 Leave Policy 2026",
                "type": "leave_policy",
                "last_modified": "2026-01-15"
            },
            {
                "id": "REC-002",
                "title": "Q1 Updated Guidelines",
                "type": "leave_policy",
                "last_modified": "2026-01-10"
            },
            {
                "id": "REC-003",
                "title": "Q1 Holiday Calendar",
                "type": "reference",
                "last_modified": "2026-01-05"
            }
        ]
    }
    
    logger.log_tool_execution_result(
        journey_id=journey_id,
        tool_name="search_records",
        result=search_results,
        execution_time=1.523,
        success=True
    )
    
    time.sleep(0.5)
    
    # STAGE 5: Journey Completion
    print("\n⏳ Completing journey...")
    
    final_response = {
        "status": "success",
        "message": "Found 3 active leave policies for Q1 2026",
        "data": search_results
    }
    
    logger.log_journey_completion(
        journey_id=journey_id,
        final_response=final_response,
        total_time=5.0,
        success=True
    )
    
    print("\n" + "="*80)
    print("JOURNEY COMPLETED SUCCESSFULLY!")
    print("="*80)
    print(f"\n✅ Journey ID: {journey_id}")
    print(f"📁 Check the logs/ directory for detailed logs")
    print(f"📄 Log files created:")
    print(f"   - logs/requests/{journey_id}.json")
    print(f"   - logs/action_plans/{journey_id}_plan.json")
    print(f"   - logs/tool_calls/{journey_id}_search_records.json")
    print(f"   - logs/audit.log")
    
    return journey_id


def example_with_error():
    """
    Demonstrate error logging.
    """
    print("\n\n" + "="*80)
    print("EXAMPLE 2: ERROR HANDLING")
    print("="*80 + "\n")
    
    logger = get_journey_logger()
    
    user_query = "Invalid operation that will fail"
    journey_id = logger.start_journey(user_query)
    
    time.sleep(0.5)
    
    # Log an error
    print("\n⏳ Simulating an error...")
    time.sleep(0.5)
    
    logger.log_error(
        journey_id=journey_id,
        error_type="ValidationError",
        error_message="Query contains invalid syntax",
        stage="intent_detection",
        stack_trace="""Traceback (most recent call last):
  File "llm/intent_router.py", line 25, in detect_intent
    data = json.loads(json_text)
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"""
    )
    
    time.sleep(0.5)
    
    # Complete journey with failure
    logger.log_journey_completion(
        journey_id=journey_id,
        final_response={"error": "Failed to process query"},
        total_time=1.234,
        success=False
    )
    
    print(f"\n✅ Error journey completed: {journey_id}")
    
    return journey_id


def example_view_logs():
    """
    Demonstrate viewing and analyzing logs.
    """
    print("\n\n" + "="*80)
    print("EXAMPLE 3: VIEWING AND ANALYZING LOGS")
    print("="*80 + "\n")
    
    analyzer = LogAnalyzer()
    
    # Show recent journeys
    print("\n📊 RECENT JOURNEYS:\n")
    analyzer.print_journey_summary(limit=5)
    
    # Get all journeys and show first one in detail
    journeys = analyzer.get_all_journeys()
    if journeys:
        first_journey = journeys[0]
        journey_id = first_journey.get("journey_id")
        
        print(f"\n📋 VIEWING FIRST JOURNEY IN DETAIL:\n")
        analyzer.print_journey_details(journey_id)
        
        # Calculate durations
        durations = analyzer.calculate_stage_durations(journey_id)
        print(f"📈 STAGE DURATIONS:")
        for stage, duration in durations.items():
            print(f"   {stage}: {duration:.3f}s" if duration else "")
        print()


def main():
    """
    Run all examples.
    """
    
    # Example 1: Complete successful journey
    journey_id_1 = example_journey_simulation()
    
    # Example 2: Journey with error
    journey_id_2 = example_with_error()
    
    # Example 3: View and analyze logs
    example_view_logs()
    
    print("\n" + "="*80)
    print("QUICK START COMPLETE!")
    print("="*80)
    print("\n📚 NEXT STEPS:")
    print("   1. Check the logs/ directory to see generated log files")
    print("   2. Read INTEGRATION_GUIDE.md to implement in your code")
    print("   3. Use logger_utils.py to analyze logs:")
    print("      python logging_config/logger_utils.py list")
    print(f"      python logging_config/logger_utils.py show {journey_id_1}")
    print("   4. Search journeys by query text:")
    print("      python logging_config/logger_utils.py search 'leave policy'")
    print("\n📖 Documentation:")
    print("   - journey_logger.py: Core logging implementation")
    print("   - INTEGRATION_GUIDE.md: How to integrate into your code")
    print("   - logger_utils.py: Tools for analyzing logs")
    print()


if __name__ == "__main__":
    main()
