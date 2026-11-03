# GitHub → AWS setup for M2_Research

This is **not yet deployed**. The GitHub workflow is manual and cannot create AWS
resources by itself. Do not deploy until you have checked account access, cost,
and data use permissions.

## 1. Local/cloud browser smoke test

Use GitHub Codespaces or any Python 3.12 terminal:

```bash
python -m unittest discover -s tests -v
python -m research_cli run-demo --articles 20 --comments 100 --output-dir /tmp/m2-demo
```

Only **synthetic** records are generated. No Naver endpoint is contacted.

## 2. Prepare AWS

1. Sign into an AWS account with IAM and CloudFormation permissions (a
   GitHub account or AWS Builder ID alone does not grant those permissions).
2. Prefer Seoul `ap-northeast-2`; configure AWS Budgets and verify the
   estimated monthly costs before creating resources.
3. In IAM, create a GitHub OIDC provider **once per AWS account**, if absent:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
4. Check the repository's **actual** OIDC subject format. New GitHub
   repositories created after July 15, 2026 use immutable IDs. The default
   for this repo is expected to be:
   `repo:manboong@50673420/M2_Research@1362711483:ref:refs/heads/main`
   If your OIDC configuration emits a different `sub`, pass
   `GitHubSubject=ACTUAL_SUB` when deploying; do not replace it with a wildcard.
5. From a terminal authenticated to the *intended* AWS account:

```bash
aws cloudformation deploy \
  --region ap-northeast-2 \
  --stack-name m2-research-core \
  --template-file infrastructure/aws/core.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-stacks \
  --region ap-northeast-2 \
  --stack-name m2-research-core \
  --query "Stacks[0].Outputs"
```

This creates an encrypted, private S3 bucket, an ECR repository named
`m2-research`, and a narrowly scoped role that can **push images to ECR only**.
It does *not* create an always-on server or start a research job. The S3 bucket
is configured for retention; deleting the stack does not delete its contents.

## 3. Configure GitHub Actions repository variables

In **Settings → Secrets and variables → Actions → Variables**, set:

| Variable | Value |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `AWS_ROLE_ARN` | `GitHubRoleArn` output from core stack |
| `AWS_ECR_REPOSITORY` | `m2-research` |

No AWS access keys are stored on GitHub. In **Actions → Publish research
container to ECR**, manually select **Run workflow** on `main`. This builds
and pushes the image with the commit SHA and `latest` tags; it does *not*
start a Batch job.

## 4. Optional: run a synthetic pipeline on AWS Batch

First publish an image. Identify the full ECR URI ending in the Git SHA tag.
Select subnets with a `0.0.0.0/0` route to an internet gateway and a security
group allowing outbound HTTPS. This template enables public IP assignment for
Fargate, but does not open inbound ports. It is an **optional**, potentially
billable step.

```bash
aws cloudformation deploy \
  --region ap-northeast-2 \
  --stack-name m2-research-batch \
  --template-file infrastructure/aws/batch.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    DataBucketName=BUCKET_FROM_CORE_OUTPUT \
    ContainerImage=ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/m2-research:COMMIT_SHA \
    SubnetIds=subnet-EXAMPLE \
    SecurityGroupIds=sg-EXAMPLE

aws batch submit-job \
  --region ap-northeast-2 \
  --job-name m2-synthetic-smoke-test \
  --job-queue QUEUE_FROM_BATCH_STACK \
  --job-definition JOB_DEFINITION_FROM_BATCH_STACK
```

Check job state and CloudWatch logs. The generated JSONL records and
`manifest.json` will appear at
`s3://BUCKET_FROM_CORE_OUTPUT/experiments/mock/RUN_ID/`. The `manifest.json`
contains record counts and SHA256 checksums; the container's Git revision is
also retained as an ECR image label.

## Boundaries and next phases

- **No Naver requests** have been implemented or authorized. Keep data source
  adapters separate until research use, collection, and retention permissions
  have been confirmed.
- The current Python example is a **smoke test** for weighted user–article
  edges, not yet a production preprocessing or SBM inference implementation.
- Batch job definition references a specific image SHA. Update it deliberately
  when you want to run a new code version, rather than automatically rerunning
  costly analyses on every push.
- AWS pricing depends on region, logs, requests, storage and task runtime;
  set billing alerts and do not treat budgets as a hard spending limit.
- If the repository stays public, never commit credentials, private data,
  hashed real-user identifiers, restricted article/comment text, or secrets.
