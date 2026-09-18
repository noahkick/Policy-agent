import json


def load_policies(path="data/policies.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

    
