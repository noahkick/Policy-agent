from dataclasses import dataclass


@dataclass
class Policy:
    policy_id: str
    version: str
    effective_date: str
    region: str
    department: str
    vendor: str
    supersedes: str | None
    content: str