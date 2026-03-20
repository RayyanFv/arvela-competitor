from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class DoDValidator:
    def validate(self, text: str, rules: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        failed: List[str] = []
        for rule in rules:
            if not rule.get("required", True):
                continue
            rule_id = rule.get("id", "unknown_rule")
            check = rule.get("check", "present")
            value = rule.get("value")
            if not self._check(text, check, value):
                failed.append(rule_id)
        return len(failed) == 0, failed

    def _check(self, text: str, check: str, value: Any) -> bool:
        if check == "min_words":
            return len(text.split()) >= int(value or 0)
        if check == "contains_keyword":
            keywords = value if isinstance(value, list) else [value]
            low = text.lower()
            return any(str(k).lower() in low for k in keywords if k)
        if check == "exactly":
            if not isinstance(value, dict):
                return False
            prefix = str(value.get("prefix", "## "))
            count = int(value.get("count", 0))
            actual = len([ln for ln in text.splitlines() if ln.startswith(prefix)])
            return actual == count
        if check == "min_rows":
            # For markdown tables, count body rows only.
            lines = [ln for ln in text.splitlines() if "|" in ln]
            body = [ln for ln in lines if not re.match(r"^\|?\s*-", ln)]
            return len(body) >= int(value or 0)
        if check == "present":
            if value is None:
                return bool(text.strip())
            needles = value if isinstance(value, list) else [value]
            low = text.lower()
            return all(str(n).lower() in low for n in needles if n)
        return False
