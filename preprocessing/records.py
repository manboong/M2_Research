"""Strict, lossless identifiers and canonical comment records."""
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return dt.astimezone(timezone.utc)


def week_of(dt):
    day = dt.astimezone(KST).date()
    return (day - timedelta(days=day.weekday())).isoformat()


def identifier(value, field):
    if isinstance(value, (float, bool)) or value is None or not str(value).strip():
        raise ValueError(f"{field}: expected a nonempty string or integer ID")
    return str(value).strip()


@dataclass(frozen=True)
class Comment:
    publisher: str
    article: str
    id: str
    user: str
    parent: str
    time: datetime
    text: str
    reply: bool

    @property
    def key(self):
        return self.publisher, self.article, self.id

    @property
    def article_key(self):
        return self.publisher, self.article

    @property
    def week(self):
        return week_of(self.time)


def rows(path):
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".csv":
            yield from csv.DictReader(stream)
        elif path.suffix.lower() == ".jsonl":
            for line in stream:
                if line.strip():
                    yield json.loads(line)
        else:
            raise ValueError("input must be CSV or JSONL")


def load_comments(path):
    """Canonical CSV and existing Naver field aliases are supported.

    Invalid rows fail the run; identical duplicates are counted, conflicting
    duplicates fail. Root self-parent pointers are supported only at level 0.
    """
    records, duplicates = {}, 0
    for number, row in enumerate(rows(path), 1):
        def get(name, alias, default=None):
            return row[name] if name in row else row.get(alias, default)
        try:
            cid = identifier(get("comment_id", "commentNo"), "comment_id")
            parent = get("parent_id", "parentCommentNo", "")
            parent = "" if parent in (None, "", 0, "0") else identifier(parent, "parent_id")
            level = get("reply_level", "replyLevel")
            if level not in (None, "") and (str(level) not in {"0", "1", "2"}):
                raise ValueError("reply_level must be 0, 1 or 2")
            reply = (int(level) > 0) if level not in (None, "") else parent not in ("", cid)
            if not reply and parent not in ("", cid):
                raise ValueError("root comment has a different parent")
            record = Comment(
                identifier(get("publisher_id", "oid"), "publisher_id"),
                identifier(get("article_id", "aid"), "article_id"), cid,
                identifier(get("user_id", "userIdNo"), "user_id"),
                parent if reply else "", timestamp(get("created_at", "reg_time_utc")),
                str(get("text", "contents", "") or ""), reply)
            if record.key in records:
                if records[record.key] != record:
                    raise ValueError("conflicting duplicate comment ID")
                duplicates += 1
            records[record.key] = record
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f"record {number}: {error}") from error
    if not records:
        raise ValueError("no comment records found")
    return sorted(records.values(), key=lambda c: (c.time, c.key)), duplicates
