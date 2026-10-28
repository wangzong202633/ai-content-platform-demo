# -*- coding: utf-8 -*-
"""Content lifecycle state machine (PRD 4.5, arch 5.2).

draft → generating → pending_supervisor → pending_boss → confirmed → distributed
                     ↑↓ reject               ↑↓ reject
                  pending_revision ←──────┘
"""

STATUSES = {
    "draft": "草稿",
    "generating": "AI生成中",
    "pending_supervisor": "待初审",
    "pending_revision": "待修改",
    "pending_boss": "待终审",
    "confirmed": "已确认",
    "distributed": "已分发",
}

# (current_status, role, action) -> next_status
TRANSITIONS = {
    ("pending_supervisor", "supervisor", "approve"): "pending_boss",
    ("pending_supervisor", "supervisor", "reject"): "pending_revision",
    ("pending_boss", "boss", "approve"): "confirmed",
    ("pending_boss", "boss", "reject"): "pending_revision",
    ("confirmed", "supervisor", "distribute"): "distributed",
}


def transition(status: str, role: str, action: str):
    nxt = TRANSITIONS.get((status, role, action))
    if nxt is None:
        raise ValueError(
            f"非法流转：状态「{STATUSES.get(status, status)}」下角色 {role} 不能执行 {action}"
        )
    return nxt


def role_for_status(status: str):
    """Which role should act on this status (for the review inbox)."""
    return {
        "pending_supervisor": "supervisor",
        "pending_boss": "boss",
    }.get(status)
