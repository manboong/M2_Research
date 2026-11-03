"""Minimal research pipeline CLI. Runs locally or inside an AWS Batch container."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from collector.mock import generate_mock, write_jsonl
from network.construction.bipartite import aggregate_edges


def run_demo(args: argparse.Namespace) -> dict:
    articles, comments = generate_mock(args.articles, args.comments, args.seed)
    edges = aggregate_edges(comments)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "articles": output_dir / "articles.jsonl",
        "comments": output_dir / "comments.jsonl",
        "edges": output_dir / "edges.jsonl",
    }
    for name, records in (("articles", articles), ("comments", comments), ("edges", edges)):
        write_jsonl(paths[name], records)

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    # Do not embed source text or credentials in manifests.
    manifest = {
        "source": "synthetic",
        "run_id": run_id,
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "seed": args.seed,
        "article_count": len(articles),
        "comment_count": len(comments),
        "edge_count": len(edges),
        "files": {
            name: {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.s3_bucket:
        import boto3  # Imported only when S3 is requested.

        prefix = args.s3_prefix.strip("/") + "/" + run_id
        s3 = boto3.client("s3")
        for path in [*paths.values(), manifest_path]:
            s3.upload_file(str(path), args.s3_bucket, f"{prefix}/{path.name}")
        manifest["s3_uri"] = f"s3://{args.s3_bucket}/{prefix}/"
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="M2_Research batch-friendly utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("run-demo", help="Synthetic data to weighted graph")
    demo.add_argument("--articles", type=int, default=100)
    demo.add_argument("--comments", type=int, default=1000)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--output-dir", default="/tmp/m2-research-output")
    demo.add_argument("--s3-bucket", default=os.environ.get("M2_S3_BUCKET"))
    demo.add_argument("--s3-prefix", default="experiments/mock")
    demo.add_argument("--run-id", default=None)
    args = parser.parse_args()
    if args.command == "run-demo":
        print(json.dumps(run_demo(args), indent=2))


if __name__ == "__main__":
    main()
