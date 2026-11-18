"""Validated annotations, kept separate from participation and vote counts."""
from preprocessing.records import rows, identifier


def load_labels(user_path=None, reply_path=None):
    users, replies = {}, {}
    if user_path:
        for row in rows(user_path):
            key = (row["week"], identifier(row["user_id"], "user_id"))
            label = row["ideology"]
            if label not in {"L", "R", "unknown"}:
                raise ValueError("ideology must be L, R or unknown")
            if key in users:
                raise ValueError(f"duplicate user annotation: {key}")
            users[key] = label
    if reply_path:
        for row in rows(reply_path):
            key = tuple(identifier(row[k], k) for k in
                        ("publisher_id", "article_id", "comment_id"))
            if key in replies:
                raise ValueError(f"duplicate reply annotation: {key}")
            if row["stance"] not in {"support", "oppose", "unclear"}:
                raise ValueError("stance must be support, oppose or unclear")
            if row["hostility"] not in {"yes", "no", "unknown"}:
                raise ValueError("hostility must be yes, no or unknown")
            replies[key] = row
    return users, replies


def validate_annotation_keys(comments, edges, users, replies):
    valid_users = {(c.week, c.user) for c in comments}
    valid_users.update((e.comment.week, e.target) for e in edges)
    valid_replies = {e.comment.key for e in edges}
    if set(users) - valid_users:
        raise ValueError("user annotations contain unknown user/week keys")
    if set(replies) - valid_replies:
        raise ValueError("reply annotations contain unresolved or unknown replies")
