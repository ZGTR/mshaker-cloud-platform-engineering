# 03 · OpenTelemetry (OTel) — the USB-C of Observability

- **Video:** <https://www.youtube.com/watch?v=qX1pwf6njX4>
- **Length:** 17:14 · **Type:** Theory

> **What you'll learn**
> - Why OTel exists (life before 2019) and what it solves
> - The **4 core components**: API, SDK, Auto-instrumentation, Collector
> - **OTLP** + **context propagation** (the connective tissue)
> - A minimal Collector YAML and the trace waterfall

---

## 1. The problem OTel solves

Before OTel, each vendor needed its **own agent** baked into your app code.

```
  BEFORE OTel (pre-2019)               WITH OpenTelemetry
  ┌─────┐  DataDog agent ─▶ DataDog    ┌─────┐            ┌──────────┐ ─▶ Datadog
  │ APP │  New Relic agent ─▶ NR       │ APP │ ─ OTel ─▶  │   OTel   │ ─▶ Honeycomb
  │     │  Jaeger SDK ─▶ Jaeger        │     │            │ Collector│ ─▶ Elastic
  └─────┘  (rewrite code per vendor)   └─────┘            └──────────┘ ─▶ Grafana
   vendor lock-in, high maintenance     instrument ONCE, route anywhere
```

| Pain (before) | Fix (OTel) |
|---------------|-----------|
| Different agent per vendor | One universal standard (CNCF) |
| Switching vendor = rewrite code | Change a `config.yaml`, ~zero cost |
| Vendor lock-in | Many backends via one Collector |
| High maintenance (fragmented agents) | One protocol, community-backed |

---

## 2. "USB-C of observability"

```
  Old world: a different adapter per device      OTel: one universal port
   ┌──┐ 2-pin ─▶ Datadog                          ┌─────┐
   ┌──┐ 3-pin ─▶ New Relic           vs           │ APP │══ USB-C ══▶ any backend
   ┌──┐ round ─▶ Jaeger                            └─────┘
```

---

## 3. The 4 core components

```
  ┌──────────────────┬───────────────────────────────────────────────┐
  │ API              │ "the MENU" — start a span, emit a log.         │
  │                  │  Lists options, doesn't cook. Vendor-neutral.  │
  ├──────────────────┼───────────────────────────────────────────────┤
  │ SDK              │ "the KITCHEN" — actual logic: batching,        │
  │                  │  retries, sampling.                            │
  ├──────────────────┼───────────────────────────────────────────────┤
  │ AUTO-INSTRUMENT  │ records HTTP calls & DB queries automatically  │
  │                  │  — zero manual code.                           │
  ├──────────────────┼───────────────────────────────────────────────┤
  │ COLLECTOR        │ "the POST OFFICE" — receive telemetry, filter, │
  │                  │  route to the backend(s) you configure.        │
  └──────────────────┴───────────────────────────────────────────────┘
```

---

## 4. Connective tissue: OTLP + context propagation

- **OTLP** (OpenTelemetry Protocol) — the agreed-upon *language* telemetry
  travels in; you point data at an **OTLP endpoint**.
- **Context propagation** — a unique **trace ID** injected into the HTTP header,
  stitching one user request across every service ("parcel tracking number").

```
  login ─▶ [trace_id=a1b2] ─▶ SERVICE A ─▶ SERVICE B ─▶ SERVICE C ─▶ DB
            injected into        (same trace_id rides the HTTP header all the way)
            HTTP header          ⇒ end-to-end view of one request
```

---

## 5. Full journey of a trace

```
  TRIGGER          AUTO-INSTR     CONTEXT-PROP    SDK         OTLP       COLLECTOR
  user clicks  ─▶  generate   ─▶  attach      ─▶ batch    ─▶ travel  ─▶ filter +
  "Checkout"       a span         trace ID        data       via OTLP    route
                                                                          │
                              ┌───────────────────────────────────────────┘
                              ▼
                  Prometheus / Jaeger / Elastic / Honeycomb / ...
```

---

## 6. A minimal Collector YAML

```yaml
receivers:                 # HOW data comes in
  otlp:
    protocols:
      grpc:                # service-to-service
      http:                # standard HTTP

exporters:                 # WHERE it goes (add more = add a line)
  jaeger:
  elastic:
  # honeycomb:

service:                   # the PIPELINE wiring receivers → exporters
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [jaeger, elastic]
```

> Add a new backend = add an entry under `exporters`. **No app code rewrite.**

---

## 7. The trace waterfall

```
  trace_id / span_id            duration
  frontend  ▇                    5 ms
  checkout  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇  120 µs  ◀── longest span = the bottleneck
  payment   ▇▇▇                  30 µs
  ──────────────────────────────────────▶
  Read top→bottom: longest bar tells you exactly where to look.
```

---

## 8. Who benefits (personas)

```
  DEVELOPER        learn ONE API; instrument once; never rewrite per vendor
  DEVOps ENGINEER  vendor-neutral YAML pipeline; swap backend by pointing
                   the Collector at a new destination
  PLATFORM ENG     central control of sampling rates, PII scrubbing,
                   and backend routing from one Collector fleet
```

> **PII** = personally identifiable information (email, phone, address) — the
> Collector can scrub it before export.

---

## Key takeaways

1. OTel is **one open standard (CNCF)** that works with any backend — instrument **once**, send anywhere.
2. **4 components:** API · SDK · Auto-instrumentation · Collector.
3. **OTLP** = the language; **context propagation** = trace IDs stitching requests together.
4. **Zero-code barrier:** auto-instrumentation + Collector config get you full traces without touching app code.

**Next:** [04 · SLO vs SLI vs SLA & Error Budget](04-slo-sli-sla-error-budget.md)
