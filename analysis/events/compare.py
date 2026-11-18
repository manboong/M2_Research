"""Descriptive pre/post weekly contrasts; deliberately no causal attribution."""
from datetime import date, timedelta
from preprocessing.records import rows


def compare(weekly, event_path, window=4):
    if window < 1:
        raise ValueError("event window must be positive")
    output = []
    for event in rows(event_path):
        day = date.fromisoformat(event["date"])
        event_week = day - timedelta(days=day.weekday())
        # Exclude the entire event week to avoid mixing pre/post observations.
        before = [r for r in weekly if event_week - timedelta(weeks=window)
                  <= date.fromisoformat(r["week"]) < event_week]
        after = [r for r in weekly if event_week < date.fromisoformat(r["week"])
                 <= event_week + timedelta(weeks=window)]
        for metric in ("cross_rate", "cross_hostile_rate", "within_hostile_rate",
                       "cross_observed_expected", "largest_component_fraction"):
            pre = [r[metric] for r in before if r[metric] is not None]
            post = [r[metric] for r in after if r[metric] is not None]
            a, b = sum(pre) / len(pre) if pre else None, sum(post) / len(post) if post else None
            output.append(dict(event=event["event"], date=event["date"], metric=metric,
                               pre_weeks=len(pre), post_weeks=len(post), pre_mean=a,
                               post_mean=b, delta=b-a if a is not None and b is not None else None))
    return output
