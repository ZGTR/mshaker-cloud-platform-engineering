# 06 · AI Observability Agent — Elasticsearch + GKE + GitHub Actions

- **Video:** <https://www.youtube.com/watch?v=kublq2Y9dNs>
- **Length:** 36:53 · **Type:** Hands-on project

> **What you'll build**
> An end-to-end **AI observability** pipeline on **GKE**. Every commit ships its
> metadata to **Elasticsearch** via **OpenTelemetry**; **Argo CD** deploys to the
> cluster; K8s events also flow to Elastic. An **Elastic Agent Builder** agent
> ("blame-the-deploy") then ties a crash (e.g. **OOMKilled**) back to the exact
> **commit** that caused it — root cause in seconds.

---

## The problem

```
  Prod crashes ─▶ war room ─▶ kubectl get logs/events/describe ... (hours)
              ─▶ finally find "a bad commit did it" ─▶ roll back.

  Gap: most tools DON'T link the diagnosis back to the commit ID.
       This project closes that gap with an AI agent.
```

## Architecture

```
  DEV merges PR ──▶ GitHub  ──┬──▶ GitHub Actions ──OTel──▶ ES index:
                              │                              github_deployment
                              │     (commit sha, author,     (commit metadata)
                              │      msg, diff_url, image)
                              │
                              └──▶ Argo CD (polls every 3m→30s)
                                      │ deploy
                                      ▼
                            ┌──── GKE cluster ────┐
                            │ Online Boutique app │ ──OTel──▶ ES index:
                            │ + OTel Operator     │           k8s events/logs
                            └─────────────────────┘
                                      │
                                      ▼
                         ┌──────────── Elasticsearch + Kibana ───────────┐
                         │  Agent Builder                                 │
                         │   tools: get_crash_logs (OOMKilled)            │
                         │          get_deploy_history (github_deployment)│
                         │   agent: "blame-the-deploy" (SRE prompt)       │
                         └────────────────────────────────────────────────┘
```

---

## Prerequisites

- Google Cloud SDK (`gcloud`), `kubectl`, `helm`, `argocd` CLI, `gh` CLI, `git`.
- A **GKE** cluster (created in advance in the video).
- **Elastic Cloud** via **GCP Marketplace** (prebuilt production image; 7-day trial).

---

## Hands-on steps

### 1 · Connect to GKE + deploy the app

```bash
gcloud container clusters get-credentials <cluster>   # from console "Connect"
kubectl get nodes                                     # 3 nodes Ready

git clone <online-boutique-repo> && cd <repo>         # microservices preconfigured
```

### 2 · Subscribe Elastic via GCP Marketplace

```
GCP Console → Marketplace → "Elastic Cloud (Elasticsearch Service)"
→ Subscribe → Manage on provider → cloud.elastic.co
→ Create hosted deployment → solution: "Elastic for Observability"
→ name: demo-deploy → Create  (≈5 min; COPY the elastic password!)
```

### 3 · Install the OTel operator into GKE

```bash
# add repo
helm repo add open-telemetry <otel-helm-repo>

# create namespace + secret (ELASTIC OTLP endpoint + API key) and install operator
kubectl create namespace opentelemetry
# the marketplace flow gives you a ready-made command containing:
#   elastic OTLP endpoint + elastic API key
helm install ... open-telemetry/opentelemetry-operator ...

kubectl get all -n <otel-namespace>   # replicasets/deploys/daemonsets/pods Up
```

```
  OTel Operator (CRDs + CRs + deploy + svc) ──▶ collects logs/metrics/traces
  from GKE ──OTLP──▶ Elasticsearch
```

### 4 · GitHub Actions → Elasticsearch (commit metadata)

`.github/workflows/index-deploy.yml` (conceptually):

```yaml
on:
  push:
    branches: [ main ]
jobs:
  detect-change-service:
    runs-on: ubuntu-latest
    steps:
      - # git diff + regex → detect changed service from manifests
      - # push deploy event to Elasticsearch using secrets:
        #   ES endpoint + ES API key
        #   payload: timestamp, commit_sha, author, service,
        #            image_tag, change(commit msg), diff_url
```

```
  push to main ─▶ GH Action ─OTel─▶ ES index "github_deployment"
                 (the breadcrumb that links a crash → a commit)
```

### 5 · Create the ES index + get endpoint/API key

```bash
# Elastic Cloud → Manage deployment → copy Elasticsearch PUBLIC endpoint
# Kibana → Settings → Security → API keys → Create API key ("test") → copy

curl -X PUT "$ES_ENDPOINT/github_deployment" \
  -H "Authorization: ApiKey $ES_API_KEY" -H 'Content-Type: application/json'
# → {"acknowledged":true, ... "index":"github_deployment"}
```

### 6 · Add GitHub secrets + test the pipeline

```bash
gh secret set ELASTICSEARCH_API_KEY  --body "$ES_API_KEY"
gh secret set ELASTICSEARCH_ENDPOINT --body "https://<host>:443"

git commit --allow-empty -m "test 2.0 verify ES indexing"
git push                              # GH Action ships metadata to ES
gh run list                           # confirm the run
```

### 7 · Install + configure Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f <argocd-install-manifest>
kubectl rollout status deploy/argocd-server -n argocd
kubectl get svc -n argocd argocd-server          # EXTERNAL-IP

# admin password (base64-encoded, not encrypted):
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d

argocd login <EXTERNAL-IP>
argocd app create online-boutique \
  --repo <YOUR_REPO_URL> --path <manifests> \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace online-boutique \
  --sync-policy automated --auto-prune --sync-option CreateNamespace=true
argocd app sync online-boutique

# speed up polling for the demo (3m → 30s) then rolling restart
kubectl -n argocd patch configmap argocd-cm --type merge \
  -p '{"data":{"timeout.reconciliation":"30s"}}'
kubectl get pods -n online-boutique -w
```

### 8 · Build the AI agent in Elastic Agent Builder

**Tool 1 — get_crash_logs** (ES|QL over the K8s logs index):

```sql
FROM logs*
| WHERE namespace == "online-boutique"
| WHERE body.text LIKE "*OOMKilled*"
| SORT @timestamp DESC
| LIMIT 20
```

**Tool 2 — get_deploy_history** (ES|QL over the commit index):

```sql
FROM github_deployment
| SORT @timestamp DESC
| LIMIT 20
```

**Agent — "blame-the-deploy"** with a master prompt:

```
You are an SRE agent. When asked why a service is crashing,
use get_crash_logs + get_deploy_history, correlate the crash
with the most recent deploy, and report the root cause + fix.
```

```
  Kibana → Agent Builder → New tool ×2 (paste ES|QL + index)
                         → New agent → add both tools → Save
```

### 9 · Run the demo — trigger an OOMKilled

Edit a manifest so the limit is below the request (forces OOM):

```yaml
# payment-service
resources:
  requests:
    memory: 24Mi
  limits:
    memory: 12Mi      # < request ⇒ OOMKilled when usage exceeds limit
```

```bash
git commit -am "optimize memory" && git push
# Argo CD detects change, tries to sync; pod restarts repeatedly (CrashLoop/OOM)
```

### 10 · Ask the agent instead of kubectl

```
Agent Builder → chat with "blame-the-deploy" (e.g. Claude Sonnet 4.5):
  "Why is payment-service crashing? Check logs and recent deployments."
```

```
  Agent calls get_crash_logs + get_deploy_history ─▶ correlates ─▶
  "Recent deploy <sha> by <author> set memory limit too low ⇒ OOMKilled.
   diff: <diff_url>.  Fix: raise the limit."   ← full RCA, tied to the commit
```

### 11 · Fix + verify

```yaml
# payment-service
resources:
  requests: { memory: 100Mi }
  limits:   { memory: 100Mi }
```

```bash
git commit -am "fix the OOMKilled issue" && git push
argocd app sync online-boutique
kubectl get pods -n online-boutique -w     # payment-service Running 1/1
```

> Ask the agent *"Is payment-service healthy now?"* — it reports **no new
> OOMKilled events**.
>
> ⚠ **Limitation shown in the video:** the `get_crash_logs` tool only matches
> `OOMKilled`. To diagnose *other* errors you must broaden the ingest patterns so
> all kubectl events / error messages reach Elasticsearch.

---

## Concept recap (ties back to docs 01–04)

```
  Traces/logs/metrics ──OTel──▶ Elasticsearch (high-cardinality store)
  GitHub Actions adds the missing dimension: COMMIT metadata
  Argo CD = GitOps reconcile (auto-recovers bad deploys)
  AI Agent = hypothesis-free exploration ⇒ crash → exact commit, no kubectl
```

## Key takeaways

1. Ship **commit metadata** to Elastic so diagnoses link back to a **commit ID**.
2. **OTel operator** streams GKE logs/events/traces into Elasticsearch.
3. **Argo CD** auto-reconciles, recovering bad deploys while you investigate.
4. An **Elastic Agent Builder** agent + ES|QL tools turns "why did it crash?" into a one-question root-cause analysis — only as good as the **log patterns** you ingest.

**Back to:** [course index](../README.md)
