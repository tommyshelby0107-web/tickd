"""One definition of "the system got this scenario right", shared by the tests and scripts/evaluate.py."""


def judge(expected: dict, decision: dict) -> tuple[bool, str]:
    outcome, reasons = decision["outcome"], set(decision["reasons"])
    if outcome not in [expected["decision"], *expected.get("acceptable", [])]:
        return False, f"expected {expected['decision']}, got {outcome}"
    if outcome != expected["decision"]:       # an allowed safe alternative, but only for an allowed reason
        ok = bool(reasons & set(expected.get("acceptable_rules", [])))
        return ok, "safe alternative" if ok else f"{outcome} for unexpected reasons {sorted(reasons)}"
    if outcome == "Approve":
        return True, "ok"
    if not set(expected.get("rules", [])) <= reasons:
        return False, f"missing rule(s) {sorted(set(expected['rules']) - reasons)}"
    if expected.get("rules_any") and not reasons & set(expected["rules_any"]):
        return False, f"none of {expected['rules_any']} fired"
    if expected.get("owner") and decision["owner"] != expected["owner"]:
        return False, f"owner {decision['owner']}, expected {expected['owner']}"
    return True, "ok"
