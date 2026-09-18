from datetime import date


def get_active_version(policies, policy_id, requested_date):

    requested = date.fromisoformat(requested_date)

    candidates = []

    for policy in policies:

        if policy["policy_id"] != policy_id:
            continue

        effective = date.fromisoformat(policy["effective_date"])

        if effective <= requested:
            candidates.append(policy)

    if not candidates:
        return None

    candidates.sort(
        key=lambda p: date.fromisoformat(p["effective_date"]),
        reverse=True
    )

    return candidates[0]


def supersedes(policy, other_policy):
    return policy["supersedes"] == other_policy["version"]
