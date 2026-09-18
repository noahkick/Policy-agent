def find_exceptions(
    policies,
    vendor=None,
    department=None,
    dataset=None
):

    results = []

    for policy in policies:

        if "EXCEPTION" not in policy["policy_id"]:
            continue

        if vendor:
            text = (
                policy["vendor"]
                + " "
                + policy["content"]
            )

            if vendor.lower() not in text.lower():
                continue

        if department:
            text = (
                policy["department"]
                + " "
                + policy["content"]
            )

            if department.lower() not in text.lower():
                continue

        if dataset:
            if dataset.lower() not in policy["content"].lower():
                continue

        results.append(policy)

    return results
