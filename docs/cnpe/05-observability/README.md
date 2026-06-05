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

## Resources
- prometheus.io, grafana.com, opentelemetry.io

## Checklist
- [ ] Golden-signal dashboards for every service
- [ ] Alerts route to a real channel
- [ ] Traces linked from metrics → logs
