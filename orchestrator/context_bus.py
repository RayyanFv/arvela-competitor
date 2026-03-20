from __future__ import annotations

from typing import Any, Dict, List


def build_start_context(company_id: str, objective: str, company_context: str, run_id: str) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "company_id": company_id,
        "objective": objective,
        "company_context": company_context,
        "_costs": {},
        "_tokens": {},
        "_dod_results": {},
        "_timestamps": {},
    }


def summarize_text(text: str, max_words: int = 400) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " ...[truncated]"


def build_agent_input(context: Dict[str, Any], context_keys: List[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key in context_keys:
        val = context.get(key, "")
        if isinstance(val, str):
            result[key] = summarize_text(val, 400)
        else:
            result[key] = val
    return result
