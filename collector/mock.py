"""Deterministic synthetic articles and comments. No network requests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random


def generate_mock(article_count: int, comment_count: int, seed: int = 42):
    """Return fully synthetic records with a stable schema for pipeline tests."""
    if article_count < 1 or comment_count < 0:
        raise ValueError("article_count must be positive and comment_count nonnegative")
    rng = random.Random(seed)
    start = datetime(2024, 12, 3, tzinfo=timezone.utc)
    articles = [
        {
            "article_id": f"synthetic_{i:06d}",
            "oid": "synthetic",
            "aid": f"{i:06d}",
            "created_at_utc": (start + timedelta(days=i % 182)).isoformat(),
            "title": f"Synthetic research article {i}",
            "source": "synthetic",
        }
        for i in range(article_count)
    ]
    comments = []
    for i in range(comment_count):
        article = articles[rng.randrange(article_count)]
        comments.append(
            {
                "comment_id": f"synthetic-comment-{i:08d}",
                "article_id": article["article_id"],
                "parent_comment_id": None,
                "user_hash": f"synthetic-user-{rng.randrange(max(4, article_count * 2)):06d}",
                "created_at_utc": (start + timedelta(days=rng.randrange(182))).isoformat(),
                "sympathy_count": rng.randrange(0, 40),
                "antipathy_count": rng.randrange(0, 40),
                "contents": f"Synthetic comment {i}; not based on real users",
                "source": "synthetic",
            }
        )
    return articles, comments


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
