# 05 · End-to-End Kubernetes Observability with Honeycomb (+ MCP)

- **Video:** <https://www.youtube.com/watch?v=TsIU47j12-A>
- **Length:** 28:26 · **Type:** Hands-on project

> **What you'll build**
> A live URL-shortener microservice app on **EKS**, instrumented with
> **OpenTelemetry**, shipping traces to **Honeycomb**. You'll add a P99 latency
> **trigger → Slack alert**, inject a **latency/chaos** spike, then root-cause it
> with Honeycomb's **BubbleUp**, **Canvas** chatbot, and **MCP**.

---

## Architecture

```
                       ┌──────────────────── EKS cluster ────────────────────┐
                       │  Nginx Ingress (AWS LB)                              │
   USER ──▶ LB DNS ──▶ │   │                                                 │
                       │   ▼   URL-shortener microservices                   │
                       │  link-svc ─ redirect-svc ─ stat-svc ─ DB            │
                       │        │ (OTel auto-instrumented build)             │
                       │        ▼                                            │
                       │   OTel: receiver → exporter → collector             │
                       └────────┼───────────────────────────────────────────┘
                                │ OTLP
                                ▼
                        ┌───────────────┐  trigger (P99>500ms)   ┌──────────┐
                        │   HONEYCOMB   │ ─────── webhook ─────▶  │  SLACK   │
                        │  (3 datasets) │                        └──────────┘
                        └──────┬────────┘
                  BubbleUp ◀───┤───▶ Canvas chatbot  ◀──▶  Honeycomb MCP (in IDE)
```

---

## Prerequisites

- A Kubernetes cluster (EKS / GKE / AKS — any works). Video uses **EKS**.
- `aws` CLI (v2: `aws sso login` / v1: `aws configure`), `kubectl`, Docker Desktop running.
- Nginx ingress controller installed.
- A **Honeycomb** free account (20M events/month free).
- A **Slack** workspace.

---

## Hands-on steps

### 1 · Provision cluster + ingress

```bash
# create EKS cluster (or use console), then:
kubectl get nodes                 # nodes Ready
kubectl get svc -n ingress-nginx  # note EXTERNAL-IP (LB DNS)
# Visiting the DNS shows 404 until the app is deployed — expected.
```

### 2 · Honeycomb API key

```
honeycomb.io → Sign up (free) → team "honeycomb-demo"
Environment: test  →  "waiting for data…"
Manage API Keys → create INGEST API key → copy
```

```bash
export HONEYCOMB_API_KEY="<your-ingest-key>"
# optionally persist in ~/.bashrc / ~/.bash_profile
```

### 3 · Slack incoming webhook

```
Slack Marketplace → "Incoming Webhook" → Add to Slack
Post to channel: #general → Add Incoming Webhook → copy WEBHOOK URL
```

### 4 · Wire the webhook into Honeycomb

```
Honeycomb → Account → Team settings → Integrations
→ "Trigger and SLO recipient" → Add integration
→ Provider: Webhook   Name: "Slack incidents"
→ paste WEBHOOK URL   (shared secret: blank)
→ enable "Trigger alerts" + paste a generic JSON alert template
→ Preview → Send (test message lands in Slack) → delete test
```

```
  Honeycomb trigger ──webhook──▶ Slack message
  { text, attachments[ {color, pretext, ...} ] }   ← JSON alert template
```

### 5 · Connect the Honeycomb MCP (in your IDE / Claude)

```bash
# add MCP server
claude mcp add honeycomb --transport <http> <honeycomb-mcp-url>
claude mcp list            # shows "needs authentication"
```

> ⚠ **Gotcha:** MCP auth needs a **configuration** key, NOT the ingest key.
> Honeycomb → Manage API Keys → create **Configuration API key** (read+write) →
> authorize. Then `get workspace context` should show your `test` environment.

### 6 · Build + deploy the instrumented app

```bash
# apply.sh clones the upstream app, copies the OTel init package,
# adds OTel deps, builds Docker images PER service (instrumented),
# loads them and deploys all manifests (secrets, config, services).
./apply.sh "$HONEYCOMB_API_KEY"
```

What `apply.sh` does, conceptually:

```
  set NAMESPACE, REPO, BUILD_DIR ─▶ check HONEYCOMB_API_KEY set
   └▶ git clone app ─▶ inject OTel init ─▶ add OTel deps
      └▶ docker build (link/redirect/stat = instrumented)
         └▶ load images ─▶ kubectl apply manifests ─▶ app live behind LB
```

Verify in Honeycomb → **3 datasets** appear, spans flowing. **Explore data**
shows events, each with a unique **trace ID** and full JSON (endpoint, library,
namespace, pod, …) you can filter.

### 7 · Create a P99 latency trigger

```
Triggers → New → Latency → dataset: redirect-service → Next
Name: "high redirect latency"   Enabled
Metric: P99   duration_ms   ≥ 500
Time window: 5 min   Frequency: every 5 min   (window ≥ frequency)
Recipient: the Slack webhook → Add → Create trigger
```

```
  IF  P99(duration_ms) ≥ 500ms  over last 5m  ──▶  page Slack
```

### 8 · Generate load + inject chaos

```bash
# terminal 1 — steady load (exports APP_URL, hits the service)
./scripts/load-test.sh

# terminal 2 — inject 800ms P99 latency (patches configmap + restarts deploy)
cd honeycomb-demo
./scripts/inject-chaos.sh        # adds chaos_active=true, latency_ms=800
```

```
  before chaos: P99 already breaching 500ms → first Slack alerts fire
  10:14 inject chaos ─▶ P99 climbs > 800ms ─▶ alert storm
```

### 9 · Root-cause it (3 ways)

**a) BubbleUp** — change the trigger query from `P99 duration_ms` to
**heatmap + duration_ms**, run, save. On the home chart, drag-select the high
band → **BubbleUp outlier**:

```
  duration_ms
   800+ ┤        ░░░░░░░░  ◀ drag-select this band
   600  ┤  ▇▇▇▇
        └───────────────▶ time
  BubbleUp diff ──▶ chaos_active=true , latency_ms=800   ← exact cause
```

**b) Canvas chatbot** — Honeycomb → Canvas:
> *"What is the cause of high P99 latency?"*
> → it queries datasets, finds redirect-service + stat-service elevated, and
> reports the ~804ms spike with a root-cause summary.

**c) MCP** — ask the *same* question from Claude/Gemini via the connected
Honeycomb MCP; you get the same summary without leaving your IDE.

---

## Concept recap (ties back to docs 01–03)

```
  OTel auto-instrumentation ─▶ traces (per-request trace IDs)
  Honeycomb = backend (high cardinality + dimensionality)
  Trigger on P99 (not average) ─▶ Slack page
  BubbleUp / Canvas / MCP ─▶ hypothesis-free exploration ⇒ instant root cause
```

## Key takeaways

1. Instrument once with **OTel**, route to **Honeycomb** as the backend.
2. Alert on **P99**, deliver via **Slack webhook** trigger.
3. **BubbleUp** visually isolates the outlier attribute (`latency_ms=800`).
4. **Canvas / MCP** let an LLM do the root-cause analysis over your telemetry.

**Next:** [06 · AI Observability Agent on GKE](06-ai-observability-agent-gke.md)
