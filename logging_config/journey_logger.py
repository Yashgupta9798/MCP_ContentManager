import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
import traceback


class JourneyLogger:
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        self._ensure_directories()
        self._setup_logging()

    def _ensure_directories(self):
        for subdir in ["", "requests", "action_plans", "tool_calls", "errors"]:
            os.makedirs(os.path.join(self.logs_dir, subdir), exist_ok=True)

    def _setup_logging(self):
        self.logger = logging.getLogger("JourneyTracker")
        self.logger.setLevel(logging.DEBUG)

        handler = logging.FileHandler(
            os.path.join(self.logs_dir, "audit.log"),
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def start_journey(self, user_query: str) -> str:
        journey_id = f"JOURNEY_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        data = {
            "journey_id": journey_id,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "stages": {}
        }
        self._write_log(f"{self.logs_dir}/requests/{journey_id}.json", data)
        self.logger.info(f"[JOURNEY_START] {journey_id} | {user_query}")
        return journey_id

    def log_intent_detection(self, journey_id: str, intent: str, confidence=None):
        self._append(journey_id, "intent_detection", {
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "confidence": confidence
        })

    def log_rag_retrieval(self, journey_id: str, query, retrieved_docs, retrieval_time):
        self._append(journey_id, "rag_retrieval", {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "retrieved_docs": retrieved_docs,
            "retrieval_time": retrieval_time
        })

    def log_action_plan(self, journey_id: str, action_plan: Dict[str, Any], generation_time=None):
        operation = action_plan.get("operation")
        method = action_plan.get("method")

        derived_tool = (
            "search_records" if operation == "SEARCH" and method == "GET"
            else "create_record" if operation == "CREATE" and method == "POST"
            else "unknown"
        )

        self._append(journey_id, "action_plan", {
            "timestamp": datetime.now().isoformat(),
            "action_plan": action_plan,
            "generation_time": generation_time
        })

        self._write_log(
            f"{self.logs_dir}/action_plans/{journey_id}_plan.json",
            action_plan
        )

        self.logger.info(
            f"[ACTION_PLAN] Journey={journey_id} | Tool={derived_tool} | Method={method}"
        )

    def log_tool_execution_start(self, journey_id, tool_name, arguments):
        self._append(journey_id, "tool_execution", {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "arguments": arguments,
            "status": "started"
        })

    def log_tool_execution_result(self, journey_id, tool_name, result, execution_time, success=True, error=None):
        self._append(journey_id, "tool_execution", {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "success": success,
            "execution_time": execution_time,
            "result": result,
            "error": error
        })

    def log_error(self, journey_id, error_type, error_message, stage, stack_trace=None):
        error = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "stage": stage,
            "stack_trace": stack_trace
        }
        self._append(journey_id, "error", error)
        self._write_log(
            f"{self.logs_dir}/errors/{journey_id}_{stage}_error.json",
            error
        )

    def log_journey_completion(self, journey_id, final_response, total_time=None, success=True):
        self._append(journey_id, "completion", {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "total_time": total_time,
            "final_response": final_response
        })

    def _write_log(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _append(self, journey_id, stage, data):
        path = f"{self.logs_dir}/requests/{journey_id}.json"
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        j.setdefault("stages", {}).setdefault(stage, []).append(data)
        j["updated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(j, f, indent=2, default=str)


_journey_logger = None

def get_journey_logger():
    global _journey_logger
    if not _journey_logger:
        _journey_logger = JourneyLogger()
    return _journey_logger
