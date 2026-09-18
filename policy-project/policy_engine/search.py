def search_policy(
    policies,
    policy_id=None,
    region=None,
    department=None,
    vendor=None,
    keyword=None
):
    results = []

    for policy in policies:

        if policy_id:
            if policy["policy_id"] != policy_id:
                continue

        if region:
            if policy["region"] not in ["GLOBAL", region]:
                continue

        if department:
            if policy["department"] not in ["ALL", department]:
                continue

        if vendor:
            if policy["vendor"] not in ["ALL", vendor]:
                continue

        if keyword:
            if keyword.lower() not in policy["content"].lower():
                continue

        results.append(policy)

    return results