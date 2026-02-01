"""
Journey Logger - Tracks the complete flow from user query to response
This module provides comprehensive logging for debugging and monitoring the 
query processing pipeline across all components.

Usage:
    from logging_config.journey_logger import JourneyLogger
    
    logger = JourneyLogger()
    journey_id = logger.start_journey(user_query)
    logger.log_intent_detection(journey_id, detected_intent)
    logger.log_action_plan(journey_id, action_plan)
    logger.log_tool_execution(journey_id, tool_name, arguments, result)
    logger.log_journey_completion(journey_id, final_response)
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import traceback


class JourneyLogger:
    """
    Centralized logging system for tracking query-to-response journey.
    Logs are organized in the logs/ directory structure.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize the journey logger.
        
        Args:
            logs_dir: Base directory for all logs (default: 'logs')
        """
        self.logs_dir = logs_dir
        self._ensure_directories()
        self._setup_logging()
        
    def _ensure_directories(self):
        """Create necessary log directories if they don't exist."""
        subdirs = [
            "",  # root logs dir
            "requests",
            "action_plans",
            "tool_calls",
            "errors",
            "journeys"
        ]
        
        for subdir in subdirs:
            path = os.path.join(self.logs_dir, subdir)
            os.makedirs(path, exist_ok=True)
    
    def _setup_logging(self):
        """Setup the main logger with file and console handlers."""
        self.logger = logging.getLogger("JourneyTracker")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler for audit log
        audit_handler = logging.FileHandler(
            os.path.join(self.logs_dir, "audit.log"),
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        audit_handler.setFormatter(formatter)
        
        self.logger.addHandler(audit_handler)
    
    def start_journey(self, user_query: str) -> str:
        """
        Log the start of a new query journey.
        
        Args:
            user_query: The user's input query
            
        Returns:
            str: A unique journey ID for tracking this request
        """
        journey_id = self._generate_journey_id()
        
        journey_data = {
            "journey_id": journey_id,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "status": "started",
            "stages": {}
        }
        
        # Log to requests directory
        self._write_log(
            os.path.join(self.logs_dir, "requests", f"{journey_id}.json"),
            journey_data
        )
        
        # Log to audit
        self.logger.info(f"[JOURNEY_START] ID={journey_id} | Query: {user_query[:100]}")
        
        print(f"\n{'='*70}")
        print(f"🔍 JOURNEY STARTED - ID: {journey_id}")
        print(f"   Query: {user_query}")
        print(f"   Time: {journey_data['timestamp']}")
        print(f"{'='*70}\n")
        
        return journey_id
    
    def log_intent_detection(self, journey_id: str, intent: str, 
                           confidence: Optional[float] = None):
        """
        Log the detected intent from the LLM.
        
        Args:
            journey_id: The journey ID
            intent: The detected intent (e.g., 'SEARCH', 'CREATE', 'UPDATE', 'HELP')
            confidence: Optional confidence score (0-1)
        """
        intent_data = {
            "stage": "intent_detection",
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "confidence": confidence
        }
        
        self._append_to_journey(journey_id, "intent_detection", intent_data)
        
        self.logger.info(
            f"[INTENT_DETECTED] Journey={journey_id} | Intent={intent} | "
            f"Confidence={confidence}"
        )
        
        print(f"📋 STAGE 1: INTENT DETECTION")
        print(f"   Intent: {intent}")
        if confidence:
            print(f"   Confidence: {confidence:.2%}")
        print()
    
    def log_rag_retrieval(self, journey_id: str, query: str, 
                         retrieved_docs: list, retrieval_time: float):
        """
        Log the RAG (Retrieval-Augmented Generation) retrieval results.
        
        Args:
            journey_id: The journey ID
            query: The query used for retrieval
            retrieved_docs: List of retrieved documents
            retrieval_time: Time taken for retrieval in seconds
        """
        rag_data = {
            "stage": "rag_retrieval",
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "retrieved_docs_count": len(retrieved_docs) if isinstance(retrieved_docs, list) else 0,
            "retrieval_time_seconds": retrieval_time,
            "documents": retrieved_docs
        }
        
        self._append_to_journey(journey_id, "rag_retrieval", rag_data)
        
        self.logger.info(
            f"[RAG_RETRIEVAL] Journey={journey_id} | Docs={len(retrieved_docs) if isinstance(retrieved_docs, list) else 0} | "
            f"Time={retrieval_time:.2f}s"
        )
        
        print(f"🔎 STAGE 2: RAG RETRIEVAL")
        print(f"   Documents Retrieved: {len(retrieved_docs) if isinstance(retrieved_docs, list) else 0}")
        print(f"   Retrieval Time: {retrieval_time:.3f}s")
        if isinstance(retrieved_docs, list) and retrieved_docs:
            print(f"   Sample Docs: {retrieved_docs[:2]}")
        print()
    
    def log_action_plan(self, journey_id: str, action_plan: Dict[str, Any],
                       generation_time: Optional[float] = None):
        """
        Log the generated action plan.
        
        Args:
            journey_id: The journey ID
            action_plan: The action plan dictionary from ActionPlanGenerator
            generation_time: Optional time taken to generate plan in seconds
        """
        plan_data = {
            "stage": "action_plan_generation",
            "timestamp": datetime.now().isoformat(),
            "action_plan": action_plan,
            "generation_time_seconds": generation_time
        }
        
        self._append_to_journey(journey_id, "action_plan", plan_data)
        
        # Also save to action_plans directory
        self._write_log(
            os.path.join(self.logs_dir, "action_plans", f"{journey_id}_plan.json"),
            action_plan
        )
        
        self.logger.info(
            f"[ACTION_PLAN] Journey={journey_id} | Tool={action_plan.get('tool', 'N/A')} | "
            f"Method={action_plan.get('method', 'N/A')} | Time={generation_time}"
        )
        
        print(f"📝 STAGE 3: ACTION PLAN GENERATED")
        print(f"   Tool: {action_plan.get('tool', 'N/A')}")
        print(f"   Method: {action_plan.get('method', 'N/A')}")
        print(f"   Generation Time: {generation_time:.3f}s" if generation_time else "")
        print(f"   Plan Details:")
        for key, value in action_plan.items():
            if key not in ['tool', 'method']:
                print(f"      {key}: {value}")
        print()
    
    def log_tool_execution_start(self, journey_id: str, tool_name: str,
                                arguments: Dict[str, Any]):
        """
        Log the start of a tool execution.
        
        Args:
            journey_id: The journey ID
            tool_name: Name of the tool being executed
            arguments: Arguments passed to the tool
        """
        tool_data = {
            "stage": "tool_execution_start",
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "in_progress"
        }
        
        self._append_to_journey(journey_id, "tool_execution", tool_data)
        
        self.logger.info(
            f"[TOOL_EXEC_START] Journey={journey_id} | Tool={tool_name}"
        )
        
        print(f"🔧 STAGE 4: TOOL EXECUTION STARTED")
        print(f"   Tool: {tool_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2, default=str)[:200]}...")
        print()
    
    def log_tool_execution_result(self, journey_id: str, tool_name: str,
                                 result: Any, execution_time: float,
                                 success: bool = True, error: Optional[str] = None):
        """
        Log the result of a tool execution.
        
        Args:
            journey_id: The journey ID
            tool_name: Name of the tool that was executed
            result: The result returned by the tool
            execution_time: Time taken for execution in seconds
            success: Whether execution was successful
            error: Error message if execution failed
        """
        tool_result_data = {
            "stage": "tool_execution_result",
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "success": success,
            "execution_time_seconds": execution_time,
            "result": result if success else None,
            "error": error
        }
        
        self._append_to_journey(journey_id, "tool_execution", tool_result_data)
        
        # Save to tool_calls directory
        self._write_log(
            os.path.join(self.logs_dir, "tool_calls", f"{journey_id}_{tool_name}.json"),
            {
                "tool_name": tool_name,
                "success": success,
                "execution_time": execution_time,
                "result": result if success else None,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info(
            f"[TOOL_EXEC_RESULT] Journey={journey_id} | Tool={tool_name} | "
            f"Status={status} | Time={execution_time:.2f}s"
        )
        
        if error:
            self.logger.error(
                f"[TOOL_ERROR] Journey={journey_id} | Tool={tool_name} | Error={error}"
            )
        
        print(f"🎯 STAGE 4: TOOL EXECUTION COMPLETED")
        print(f"   Tool: {tool_name}")
        print(f"   Status: {status}")
        print(f"   Execution Time: {execution_time:.3f}s")
        if error:
            print(f"   Error: {error}")
        print(f"   Result Preview: {str(result)[:150]}..." if result else "")
        print()
    
    def log_journey_completion(self, journey_id: str, final_response: Any,
                              total_time: Optional[float] = None, success: bool = True):
        """
        Log the completion of the entire journey.
        
        Args:
            journey_id: The journey ID
            final_response: The final response to be sent to user
            total_time: Total time taken for entire journey in seconds
            success: Whether the journey completed successfully
        """
        completion_data = {
            "stage": "journey_completion",
            "timestamp": datetime.now().isoformat(),
            "status": "completed" if success else "failed",
            "final_response": final_response,
            "total_time_seconds": total_time
        }
        
        self._append_to_journey(journey_id, "completion", completion_data)
        
        status = "✅ COMPLETED" if success else "❌ FAILED"
        self.logger.info(
            f"[JOURNEY_COMPLETE] Journey={journey_id} | Status={status} | "
            f"TotalTime={total_time:.2f}s" if total_time else ""
        )
        
        print(f"{'='*70}")
        print(f"✨ JOURNEY COMPLETED - ID: {journey_id}")
        print(f"   Status: {status}")
        print(f"   Total Time: {total_time:.3f}s" if total_time else "")
        print(f"   Final Response: {str(final_response)[:100]}...")
        print(f"{'='*70}\n")
    
    def log_error(self, journey_id: str, error_type: str, error_message: str,
                 stage: str = "unknown", stack_trace: Optional[str] = None):
        """
        Log an error that occurred during the journey.
        
        Args:
            journey_id: The journey ID
            error_type: Type of error (e.g., 'LLMError', 'ToolError', 'ValidationError')
            error_message: Error message
            stage: The stage where error occurred
            stack_trace: Optional stack trace
        """
        error_data = {
            "journey_id": journey_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "stage": stage,
            "stack_trace": stack_trace
        }
        
        # Save to errors directory
        self._write_log(
            os.path.join(self.logs_dir, "errors", f"{journey_id}_{stage}_error.json"),
            error_data
        )
        
        self._append_to_journey(journey_id, "error", error_data)
        
        self.logger.error(
            f"[ERROR] Journey={journey_id} | Type={error_type} | Stage={stage} | "
            f"Message={error_message}"
        )
        
        print(f"⚠️  ERROR DETECTED")
        print(f"   Journey ID: {journey_id}")
        print(f"   Type: {error_type}")
        print(f"   Stage: {stage}")
        print(f"   Message: {error_message}")
        if stack_trace:
            print(f"   Stack Trace:\n{stack_trace}")
        print()
    
    def get_journey_log(self, journey_id: str) -> Optional[Dict]:
        """
        Retrieve the complete journey log.
        
        Args:
            journey_id: The journey ID
            
        Returns:
            dict: The complete journey log or None if not found
        """
        file_path = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def list_journeys(self, limit: int = 10) -> list:
        """
        List recent journeys.
        
        Args:
            limit: Maximum number of journeys to return
            
        Returns:
            list: List of journey IDs sorted by most recent first
        """
        requests_dir = os.path.join(self.logs_dir, "requests")
        if not os.path.exists(requests_dir):
            return []
        
        journeys = []
        for file in os.listdir(requests_dir):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(requests_dir, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        journeys.append({
                            "journey_id": data.get("journey_id"),
                            "timestamp": data.get("timestamp"),
                            "query": data.get("user_query")
                        })
                except:
                    pass
        
        # Sort by timestamp descending
        journeys.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return journeys[:limit]
    
    # ==================== Private Helper Methods ====================
    
    def _generate_journey_id(self) -> str:
        """Generate a unique journey ID based on timestamp and random suffix."""
        from random import randint
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = f"{randint(1000, 9999)}"
        return f"JOURNEY_{timestamp}_{random_suffix}"
    
    def _write_log(self, file_path: str, data: Dict[str, Any]):
        """Write data to a JSON file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to write log file {file_path}: {e}")
    
    def _append_to_journey(self, journey_id: str, key: str, data: Dict[str, Any]):
        """Append data to the journey log file."""
        journey_file = os.path.join(self.logs_dir, "requests", f"{journey_id}.json")
        try:
            if os.path.exists(journey_file):
                with open(journey_file, 'r', encoding='utf-8') as f:
                    journey_data = json.load(f)
            else:
                journey_data = {
                    "journey_id": journey_id,
                    "timestamp": datetime.now().isoformat(),
                    "stages": {}
                }
            
            if "stages" not in journey_data:
                journey_data["stages"] = {}
            
            if key not in journey_data["stages"]:
                journey_data["stages"][key] = []
            
            journey_data["stages"][key].append(data)
            journey_data["updated_at"] = datetime.now().isoformat()
            
            with open(journey_file, 'w', encoding='utf-8') as f:
                json.dump(journey_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to append to journey log: {e}")


# Singleton instance for easy access
_journey_logger_instance = None

def get_journey_logger() -> JourneyLogger:
    """
    Get the singleton instance of JourneyLogger.
    
    Returns:
        JourneyLogger: The singleton logger instance
    """
    global _journey_logger_instance
    if _journey_logger_instance is None:
        _journey_logger_instance = JourneyLogger()
    return _journey_logger_instance
