from typing import Any


def calculate_downgrade_impact(
    current_values: dict[str, Any],
    target_values: dict[str, Any],
    usage: dict[str, float],
) -> tuple[list[str], list[dict[str, Any]], bool]:
    features_lost = sorted(
        code
        for code, value in current_values.items()
        if value is True and target_values.get(code) is not True
    )
    decreases: list[dict[str, Any]] = []
    over_limit = False
    for code, old_value in current_values.items():
        if not code.startswith("quota.") or code not in target_values:
            continue
        new_value = float(target_values[code])
        if float(old_value) <= new_value:
            continue
        current_usage = usage.get(code, 0)
        is_over = current_usage > new_value
        over_limit = over_limit or is_over
        decreases.append(
            {
                "feature_code": code,
                "old_limit": float(old_value),
                "new_limit": new_value,
                "current_usage": current_usage,
                "over_limit": is_over,
            }
        )
    return features_lost, decreases, over_limit
