"""
Quick Start Example - Using the Journey Logger

This file demonstrates how to quickly implement journey logging
using the FINAL action-plan contract.

RUN THIS EXAMPLE:
    python logging_config/quick_start.py
"""

import time
from journey_logger import get_journey_logger
from logger_utils import LogAnalyzer


def example_journey_simulation():
    """
    Simulate a complete query journey to demonstrate logging.
    """

    print("\n" + "=" * 80)
    print("JOURNEY LOGGER - QUICK START EXAMPLE")
    print("=" * 80 + "\n")

    # Initialize logger
    logger = get_journey_logger()

    # Simulate a user query
    user_query = "Show me all active leave policies for Q1 2026"

    # ----------------------------
    # START JOURNEY
    # ----------------------------
    journey_id = logger.start_journey(user_query)
    time.sleep(0.5)

    # ----------------------------
    # STAGE 1: Intent Detection
    # ----------------------------
    print("⏳ Simulating intent detection...")
    time.sleep(1)

    detected_intent = "SEARCH"
    logger.log_intent_detection(
        journey_id=journey_id,
        intent=detected_intent,
        confidence=0.95
    )

    # ----------------------------
    # STAGE 2: RAG Retrieval
    # ----------------------------
    print("⏳ Simulating RAG retrieval...")
    time.sleep(0.5)

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

    # ----------------------------
    # STAGE 3: Action Plan Generation
    # ----------------------------
    print("⏳ Generating action plan...")
    time.sleep(0.5)

    # ✅ FINAL CORRECT ACTION PLAN (NO tool FIELD)
    action_plan = {
        "path": "Record/",
        "method": "GET",
        "parameters": {
            "q": "active leave policies Q1 2026",
            "format": "json",
            "properties": "NameString"
        },
        "operation": "SEARCH"
    }

    logger.log_action_plan(
        journey_id=journey_id,
        action_plan=action_plan,
        generation_time=1.234
    )

    # ----------------------------
    # STAGE 4: Tool Execution
    # ----------------------------
    print("⏳ Executing tool...")
    time.sleep(0.5)

    logger.log_tool_execution_start(
        journey_id=journey_id,
        tool_name="search_records",  # derived internally in real flow
        arguments={"action_plan": action_plan}
    )

    time.sleep(1.5)

    search_results = {
        "status": "success",
        "records_found": 3,
        "records": [
            {
                "id": "REC-001",
                "title": "Q1 Leave Policy 2026",
                "last_modified": "2026-01-15"
            },
            {
                "id": "REC-002",
                "title": "Q1 Updated Guidelines",
                "last_modified": "2026-01-10"
            },
            {
                "id": "REC-003",
                "title": "Q1 Holiday Calendar",
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

    # ----------------------------
    # STAGE 5: Journey Completion
    # ----------------------------
    print("⏳ Completing journey...")
    time.sleep(0.5)

    final_response = {
        "message": "Found 3 active leave policies for Q1 2026",
        "data": search_results
    }

    logger.log_journey_completion(
        journey_id=journey_id,
        final_response=final_response,
        total_time=5.0,
        success=True
    )

    print("\n" + "=" * 80)
    print("JOURNEY COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"✅ Journey ID: {journey_id}")
    print("📁 Check logs/ directory for generated files\n")

    return journey_id


def example_with_error():
    """
    Demonstrate error logging.
    """

    print("\n" + "=" * 80)
    print("EXAMPLE 2: ERROR HANDLING")
    print("=" * 80 + "\n")

    logger = get_journey_logger()

    user_query = "Invalid operation that will fail"
    journey_id = logger.start_journey(user_query)
    time.sleep(0.5)

    print("⏳ Simulating an error...")
    time.sleep(0.5)

    logger.log_error(
        journey_id=journey_id,
        error_type="ValidationError",
        error_message="Invalid action plan structure",
        stage="action_plan_generation"
    )

    logger.log_journey_completion(
        journey_id=journey_id,
        final_response={"error": "Failed to process query"},
        total_time=1.234,
        success=False
    )

    print(f"❌ Error journey completed: {journey_id}\n")
    return journey_id


def example_view_logs():
    """
    Demonstrate viewing and analyzing logs.
    """

    print("\n" + "=" * 80)
    print("EXAMPLE 3: VIEWING LOGS")
    print("=" * 80 + "\n")

    analyzer = LogAnalyzer()
    analyzer.print_journey_summary(limit=5)

    journeys = analyzer.get_all_journeys()
    if journeys:
        journey_id = journeys[0]["journey_id"]
        analyzer.print_journey_details(journey_id)


def main():
    journey_id_1 = example_journey_simulation()
    example_with_error()
    example_view_logs()

    print("\n" + "=" * 80)
    print("QUICK START COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Inspect logs/ directory")
    print("2. Read INTEGRATION_GUIDE.md")
    print(f"3. View journey: python logger_utils.py show {journey_id_1}\n")


if __name__ == "__main__":
    main()
