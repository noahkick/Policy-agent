def scope_specificity(policy, context):

    score = 0

    if policy["region"] != "GLOBAL":
        if policy["region"] == context.get("region"):
            score += 2

    if policy["department"] != "ALL":
        if policy["department"] == context.get("department"):
            score += 2

    if policy["vendor"] != "ALL":
        if policy["vendor"] == context.get("vendor"):
            score += 1

    return score


def find_applicable_policies(policies, context):

    matches = []

    for policy in policies:

        score = scope_specificity(policy, context)

        if score > 0:
            matches.append((score, policy))

    matches.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return matches
