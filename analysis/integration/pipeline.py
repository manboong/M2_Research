"""Reproducible local research pipeline (Python 3.10+)."""
import argparse
import csv
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from preprocessing.records import load_comments
from network.construction.replies import build_replies, participation, aggregated_replies
from nlp.dataset.annotations import load_labels, validate_annotation_keys
from analysis.weekly.summary import summarize
from analysis.events.compare import compare
from visualization.report import render_report


def write_csv(path, data, fields=None):
    fields = fields or (list(data[0]) if data else [])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"name": Path(path).name, "sha256": digest.hexdigest()}


def run(args):
    if args.null_samples < 1 or args.event_window < 1:
        raise ValueError("null samples and event window must be positive")
    output = Path(args.output)
    if output.exists():
        raise ValueError("output already exists; choose a new directory for each run")
    comments, duplicates = load_comments(args.comments)
    edges, issues = build_replies(comments)
    users, annotations = load_labels(args.users, args.annotations)
    validate_annotation_keys(comments, edges, users, annotations)
    weekly = summarize(comments, edges, issues, users, annotations, args.null_samples, args.seed)
    event_rows = compare(weekly, args.events, args.event_window) if args.events else []
    edge_rows = aggregated_replies(edges)
    sbm = None
    if args.sbm:
        from network.community.sbm import fit_weekly
        sbm = fit_weekly(edge_rows, args.seed)
    output.mkdir(parents=True)
    write_csv(output / "weekly.csv", weekly)
    write_csv(output / "reply_edges.csv", edge_rows, ["week", "source", "target", "weight"])
    write_csv(output / "reply_issues.csv", issues,
              ["publisher_id", "article_id", "comment_id", "week", "reason"])
    for kind, pub in (("user_article", False), ("user_publisher", True)):
        write_csv(output / f"{kind}.csv", participation(comments, pub))
    label_keys = {(c.week, c.user) for c in comments}
    label_keys.update((e.comment.week, e.target) for e in edges)
    write_csv(output / "user_labels_template.csv",
              [dict(week=w, user_id=u, ideology="unknown") for w, u in sorted(label_keys)])
    write_csv(output / "reply_labels_template.csv", [
        dict(publisher_id=e.comment.publisher, article_id=e.comment.article,
             comment_id=e.comment.id, parent_id=e.parent.id,
             parent_text=e.parent.text, reply_text=e.comment.text,
             stance="unclear", hostility="unknown") for e in edges],
        ["publisher_id", "article_id", "comment_id", "parent_id", "parent_text", "reply_text", "stance", "hostility"])
    if args.events:
        write_csv(output / "events.csv", event_rows,
                  ["event", "date", "metric", "pre_weeks", "post_weeks", "pre_mean", "post_mean", "delta"])
    if sbm is not None:
        write_csv(output / "sbm_memberships.csv", sbm[0], ["week", "user_id", "block"])
        write_csv(output / "sbm_models.csv", sbm[1], ["week", "nodes", "edges", "description_length", "blocks"])
    repo = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    code = hashlib.sha256()
    for folder in ("analysis", "network", "nlp", "preprocessing", "visualization"):
        for path in sorted((repo / folder).rglob("*.py")):
            code.update(path.relative_to(repo).as_posix().encode())
            code.update(path.read_bytes())
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "git_commit": commit, "git_dirty": dirty,
                "source_sha256": code.hexdigest(), "week_timezone": "UTC+09:00", "week_start": "Monday",
                "seed": args.seed, "null_samples": args.null_samples, "null_sweeps": 10,
                "event_window": args.event_window, "sbm": args.sbm,
                "comments": len(comments), "duplicate_rows_removed": duplicates,
                "reply_edges": len(edges), "reply_issue_counts": {
                    reason: sum(r["reason"] == reason for r in issues) for reason in sorted({r["reason"] for r in issues})},
                "inputs": {name: fingerprint(path) for name, path in
                           (("comments", args.comments), ("users", args.users),
                            ("annotations", args.annotations), ("events", args.events)) if path}}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "report.html").write_text(render_report(weekly, manifest), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comments", required=True, help="Canonical or Naver-alias CSV/JSONL")
    parser.add_argument("--output", required=True, help="New local output directory")
    parser.add_argument("--users", help="Weekly ideology labels CSV/JSONL")
    parser.add_argument("--annotations", help="Reply stance/hostility CSV/JSONL")
    parser.add_argument("--events", help="event,date CSV/JSONL")
    parser.add_argument("--event-window", type=int, default=4)
    parser.add_argument("--null-samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sbm", action="store_true", help="Run optional graph-tool backend")
    args = parser.parse_args()
    try:
        manifest = run(args)
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Pipeline error: {exc}\n")
    print(json.dumps({"output": args.output, "comments": manifest["comments"],
                      "reply_edges": manifest["reply_edges"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
