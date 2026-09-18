def get_evidence(policies):

    return [
        {
            "policy_id": p["policy_id"],
            "version": p["version"],
            "effective_date": p["effective_date"],
            "content": p["content"]
        }
        for p in policies
    ]