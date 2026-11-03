"""Build weighted user–article edges without external graph libraries."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


def aggregate_edges(comments: Iterable[Mapping]) -> list[dict]:
    """One edge per (user, article), weighted by distinct comment count."""
    weights: Counter[tuple[str, str]] = Counter()
    seen_comments: set[str] = set()
    for item in comments:
        comment_id = str(item["comment_id"])
        if comment_id in seen_comments:
            continue
        seen_comments.add(comment_id)
        user_id = str(item["user_hash"])
        article_id = str(item["article_id"])
        if not user_id or not article_id:
            raise ValueError("Missing user or article ID")
        weights[(user_id, article_id)] += 1
    return [
        {"user_hash": user, "article_id": article, "weight": weight}
        for (user, article), weight in sorted(weights.items())
    ]
