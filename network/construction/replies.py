"""Preserve article context and resolve parents across time windows."""
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Reply:
    comment: object
    parent: object

    @property
    def source(self):
        return self.comment.user

    @property
    def target(self):
        return self.parent.user


def build_replies(comments):
    lookup = {c.key: c for c in comments}
    edges, issues = [], []
    for c in comments:
        if not c.reply:
            continue
        p = lookup.get((*c.article_key, c.parent))
        reason = None
        if not c.parent:
            reason = "missing_parent_id"
        elif c.parent == c.id:
            reason = "self_parent_pointer"
        elif p is None:
            reason = "parent_not_in_dataset"
        elif p.time > c.time:
            reason = "parent_after_reply"
        elif p.user == c.user:
            reason = "self_reply"
        if reason:
            issues.append({"publisher_id": c.publisher, "article_id": c.article,
                           "comment_id": c.id, "week": c.week, "reason": reason})
        else:
            edges.append(Reply(c, p))
    return edges, issues


def participation(comments, publisher=False):
    counts = Counter((c.week, c.user, c.publisher,
                      "" if publisher else c.article) for c in comments)
    return [{"week": w, "user_id": u, "publisher_id": p,
             "article_id": a, "weight": n}
            for (w, u, p, a), n in sorted(counts.items())]


def aggregated_replies(edges):
    counts = Counter((e.comment.week, e.source, e.target) for e in edges)
    return [{"week": w, "source": u, "target": v, "weight": n}
            for (w, u, v), n in sorted(counts.items())]


def component_sizes(users, edges):
    """Weak components including users with no reply edges."""
    parent = {u: u for u in users}
    size = {u: 1 for u in users}
    def find(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u
    for edge in edges:
        a, b = find(edge.source), find(edge.target)
        if a != b:
            if size[a] < size[b]:
                a, b = b, a
            parent[b] = a
            size[a] += size[b]
    return sorted(Counter(find(u) for u in users).values(), reverse=True)
