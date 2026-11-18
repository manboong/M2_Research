"""Label coverage, directed mixing, semantics and a constrained null baseline."""
import random
import statistics
from collections import Counter, defaultdict


def ratio(a, b):
    return a / b if b else None


def labeled(edges, users):
    return [e for e in edges if all(users.get((e.comment.week, u)) in {"L", "R"}
                                   for u in (e.source, e.target))]


def mixing(edges, users, annotations):
    known = labeled(edges, users)
    counts = Counter((users[e.comment.week, e.source], users[e.comment.week, e.target])
                     for e in known)
    result = {f"{a}_{b}": counts[a, b] for a in "LR" for b in "LR"}
    result.update(labeled_edges=len(known), label_coverage=ratio(len(known), len(edges)),
                  cross_rate=ratio(counts["L", "R"] + counts["R", "L"], len(known)))
    for group in ("within", "cross"):
        subset = [e for e in known if
                  (users[e.comment.week, e.source] != users[e.comment.week, e.target])
                  == (group == "cross")]
        ann = [annotations[e.comment.key] for e in subset if e.comment.key in annotations]
        hostile = [a for a in ann if a["hostility"] != "unknown"]
        stance = [a for a in ann if a["stance"] != "unclear"]
        result.update({f"{group}_edges": len(subset),
                       f"{group}_hostility_labeled": len(hostile),
                       f"{group}_stance_labeled": len(stance),
                       f"{group}_hostile_rate": ratio(sum(a["hostility"] == "yes" for a in hostile), len(hostile)),
                       f"{group}_oppose_rate": ratio(sum(a["stance"] == "oppose" for a in stance), len(stance))})
    return result


def null_mixing(edges, users, samples=100, seed=42, sweeps=10):
    """Pilot MCMC: swap parent-comment targets within article and week.

    Preserves outgoing/incoming reply counts and each source timestamp. Rejects
    self-user loops and targets created after the source reply. Uses only edges
    with both ideology labels, so inference is conditional on labeled activity.
    Samples are correlated; this is NOT an exact p-value or convergence proof.
    """
    if samples < 1 or sweeps < 1:
        raise ValueError("samples and sweeps must be positive")
    edges = labeled(edges, users)
    buckets = defaultdict(list)
    for i, edge in enumerate(edges):
        buckets[(edge.comment.week, edge.comment.article_key)].append(i)
    eligible = [b for b in buckets.values() if len(b) >= 2]
    targets = [e.parent for e in edges]
    rng, accepted, attempted = random.Random(seed), 0, 0
    def cross_count():
        return sum(users[e.comment.week, e.source] != users[e.comment.week, p.user]
                   for e, p in zip(edges, targets))
    observed = cross_count()
    draws = []
    # One burn-in block followed by samples separated by proposal sweeps.
    for draw in range(samples + 1):
        for bucket in eligible:
            for _ in range(sweeps * len(bucket)):
                i, j = rng.sample(bucket, 2)
                attempted += 1
                a, b = edges[i], edges[j]
                p, q = targets[i], targets[j]
                if p.key == q.key:
                    continue
                if a.source == q.user or b.source == p.user:
                    continue
                if q.time > a.comment.time or p.time > b.comment.time:
                    continue
                if q.key == a.comment.key or p.key == b.comment.key:
                    continue
                targets[i], targets[j] = q, p
                accepted += 1
        if draw:
            draws.append(cross_count())
    mean = statistics.mean(draws) if edges else None
    sd = statistics.pstdev(draws) if edges else None
    usable = bool(accepted and sd)
    return {"null_status": "pilot_mcmc" if usable else "degenerate_or_immobile",
            "null_labeled_edges": len(edges), "cross_observed": observed,
            "cross_null_mean": mean, "cross_null_sd": sd,
            "cross_observed_expected": ratio(observed, mean) if usable else None,
            "null_samples": samples, "null_attempted": attempted,
            "null_accepted": accepted, "null_acceptance": ratio(accepted, attempted)}
