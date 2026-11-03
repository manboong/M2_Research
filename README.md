# M2_Research

Cloud-ready master's research project on **network polarization in Korean
online political discussion**. The planned workflow is collecting
(permission-dependent) article/comment data, preprocessing, constructing
user–article bipartite graphs, SBM inference, and temporal/event analysis.

## Repository layout

The original research areas remain in place:

- `collector/`: article/comment collectors and an offline synthetic-data generator
- `preprocessing/`: parsing and cleaning (planned)
- `network/`: bipartite construction, community inference, metrics
- `nlp/`: auxiliary language processing
- `analysis/`: weekly, event, and integrated analysis
- `visualization/`: research figures

## Reproducible synthetic demonstration

Requires Python 3.12. No external APIs or credentials needed:

```bash
python -m unittest discover -s tests -v
python -m research_cli run-demo --articles 100 --comments 1000 \
  --output-dir /tmp/m2-research-output --seed 42
```

This produces `articles.jsonl`, `comments.jsonl`, `edges.jsonl`,
and a checksum-bearing `manifest.json`. All records are synthetic and
suitable for pipeline testing. This smoke test is **not** an SBM result.

## GitHub + AWS

GitHub Codespaces offers a browser-only development environment. Pull requests
run tests through GitHub Actions. An opt-in GitHub Actions workflow can publish
a version-tagged Docker image to Amazon ECR through short-lived OIDC credentials.

Deployment is intentionally **manual**. For CloudFormation resources, OIDC
setup, AWS Batch execution, security constraints, and cost considerations, see
[docs/aws-setup.md](docs/aws-setup.md).

## Research data and ethics

Actual Naver collection is intentionally disabled pending appropriate
authorization. No production scraper, real-user comments or identification
data are included. Do not upload restricted research records to this public
repository. Reproducible synthetic data is used instead.
