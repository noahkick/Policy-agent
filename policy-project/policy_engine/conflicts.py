def detect_conflicts(applicable_policies):

    conflicts = []

    for i in range(len(applicable_policies)):

        for j in range(i + 1, len(applicable_policies)):

            p1 = applicable_policies[i]
            p2 = applicable_policies[j]

            if p1["policy_id"] == p2["policy_id"]:

                if p1["content"] != p2["content"]:

                    conflicts.append({
                        "policy_a": p1,
                        "policy_b": p2
                    })

    return conflicts