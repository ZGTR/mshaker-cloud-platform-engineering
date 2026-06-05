# 05 — Observability

**Pillar:** Runtime

## Goal
Know the health of every workload and the platform itself via metrics, logs,
and traces — with consistent dashboards and actionable alerts.

## Why it matters
You cannot operate what you cannot see. Observability turns incidents from
guesswork into root-cause analysis and underpins SLOs.

## What this covers
- The three pillars: metrics, logs, traces (and the four golden signals)
- Prometheus + Alertmanager; recording/alerting rules; PromQL
- Grafana dashboards and data sources
- Loki for logs; Tempo/Jaeger for traces
- OpenTelemetry: instrumentation, Collector, vendor-neutral pipelines
- SLOs / SLIs / error budgets

## Hands-on labs
- [ ] Install kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
- [ ] Scrape app + mesh metrics, build a golden-signals dashboard
- [ ] Ship logs to Loki and correlate with traces
- [ ] Instrument a service with OpenTelemetry → Collector → backend
- [ ] Define an SLO and an alert on burn rate

## Tools
Prometheus, Grafana, OpenTelemetry, Loki, Tempo/Jaeger, Alertmanager

## Follow-along notes (Observability Zero to Hero series)
Study notes + ASCII visuals for the [Tech Tutorials with Piyush](https://www.youtube.com/playlist?list=PLl4APkPHzsUWC89lwHRGxk1GDtS7dkUsE)
series, ordered for learning (fundamentals → projects):

| # | Doc | Topic | Length | Type |
|---|-----|-------|--------|------|
| 01 | [Introduction to Observability](2026-06-05-lesson-01-introduction-to-observability.md) | Monitoring vs Observability, P50/P95/P99 | 21:54 | Theory |
| 02 | [Logs, Metrics & Traces](2026-06-05-lesson-02-logs-metrics-traces.md) | The 3 pillars + 4 golden signals | 15:47 | Theory |
| 03 | [OpenTelemetry](2026-06-05-lesson-03-opentelemetry.md) | OTel: API/SDK/Auto-instr/Collector | 17:14 | Theory |
| 04 | [SLI vs SLO vs SLA + Error Budget](2026-06-05-lesson-04-slo-sli-sla-error-budget.md) | SLI/SLO/SLA + error budget | 19:15 | Theory |
| 05 | [Honeycomb K8s Project](2026-06-05-lesson-05-honeycomb-k8s-project.md) | E2E K8s obs with Honeycomb + MCP | 28:26 | Project |
| 06 | [AI Observability Agent](2026-06-05-lesson-06-ai-observability-agent-gke.md) | AI agent: Elastic + GKE + GH Actions | 36:53 | Project |

## Resources
- prometheus.io, grafana.com, opentelemetry.io

## Checklist
- [ ] Golden-signal dashboards for every service
- [ ] Alerts route to a real channel
- [ ] Traces linked from metrics → logs
