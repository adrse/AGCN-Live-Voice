from __future__ import annotations

import time
from collections import deque


class CommentFusion:
    """Agrupa comentários próximos e relacionados antes da decisão."""

    def __init__(self, window_seconds: float = 1.4, max_pending: int = 80):
        self.window_seconds = window_seconds
        self.pending = deque(maxlen=max(10, int(max_pending)))

    def add(self, analyzed: dict) -> None:
        item = dict(analyzed)
        item["received_at"] = time.time()
        self.pending.append(item)

    def ready_groups(self, force: bool = False) -> list[dict]:
        if not self.pending:
            return []

        now = time.time()
        ready = []

        while self.pending:
            first = self.pending[0]
            if not force and now - first["received_at"] < self.window_seconds:
                break
            ready.append(self.pending.popleft())

        if not ready:
            return []

        groups = []
        used = set()

        for i, item in enumerate(ready):
            if i in used:
                continue

            group = [item]
            used.add(i)

            for j in range(i + 1, len(ready)):
                other = ready[j]
                if j in used:
                    continue

                same_user = (
                    item.get("user", "").casefold()
                    == other.get("user", "").casefold()
                )
                same_topic = item.get("topic") == other.get("topic")

                if same_user or same_topic:
                    group.append(other)
                    used.add(j)

            best = max(group, key=lambda x: x.get("priority", 0))
            groups.append({
                "primary": best,
                "items": group,
                "priority": max(x.get("priority", 0) for x in group),
                "users": list(dict.fromkeys(x.get("user") for x in group if x.get("user"))),
                "topics": list(dict.fromkeys(x.get("topic") for x in group if x.get("topic"))),
            })

        return groups
