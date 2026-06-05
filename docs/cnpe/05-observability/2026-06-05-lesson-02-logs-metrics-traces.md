# 02 · Logs, Metrics & Traces — The 3 Pillars of Observability

- **Video:** <https://www.youtube.com/watch?v=GsW0-uiCwqQ>
- **Length:** 15:47 · **Type:** Theory

> **What you'll learn**
> - The 3 pillars — **logs, metrics, traces** — and when to use each
> - Structured vs unstructured logs
> - The **4 golden signals** (minimum viable observability)
> - The **cardinality trap** and the unified debugging workflow

---

## The hospital analogy

```
  ┌──────────────┬────────────────────────────┬───────────────────────────┐
  │   LOGS       │   METRICS                  │   TRACES                  │
  ├──────────────┼────────────────────────────┼───────────────────────────┤
  │ Nurse's notes│ Vital signs                │ Patient's journey map     │
  │ "3pm chest   │ heart rate / BP plotted    │ Reception → Triage →      │
  │  pain, gave  │ every 15 min               │ Radiology → ICU           │
  │  aspirin"    │ (numbers over time)        │ (path + time per hop)     │
  └──────────────┴────────────────────────────┴───────────────────────────┘
       WHAT happened        HOW MUCH / trend        WHERE in the flow
```

---

## Pillar 1 · LOGS — a record of a discrete event

```
  LOG ENTRY = TIMESTAMP  +  SEVERITY  +  CONTEXT
              2026-06-05   ERROR        "payment failed, order 5521,
              10:14:03.221              card declined"
```

Answers: **"what exactly happened with this specific thing?"**

### Structured vs Unstructured

```
  UNSTRUCTURED  (human-friendly, machine-hostile)
  ┌───────────────────────────────────────────────┐
  │ Payment failed for user John, order 5521,      │
  │ card declined                                  │  ✖ hard to parse/filter
  └───────────────────────────────────────────────┘

  STRUCTURED (JSON — machine-friendly)
  ┌───────────────────────────────────────────────┐
  │ { "ts":"...", "level":"error",                 │
  │   "order_id":5521, "user":"john@..",           │  ✔ filter at scale
  │   "service":"payment", "reason":"declined" }   │     find in 2 min not 2 hrs
  └───────────────────────────────────────────────┘
```

> With 50 services writing millions of lines/day, structured logs are the
> difference between **2 minutes** and **2 hours** to find a problem.

---

## Pillar 2 · METRICS — numbers measured repeatedly over time

Stored in a **time-series DB**. Spot *when* something changed:

```
  req/s
  2000 ┤                    ╭─────  ← spike! something happened HERE
       │                   ╱
  1000 ┤                 ╭╯
   500 ┤────────────────╯
       └────────────────────────────▶ time
```

### The 4 Golden Signals (minimum viable observability)

```
  ┌────────────┬──────────────────────────────┬───────────────────────┐
  │ LATENCY    │ how long to respond?         │ drives user experience│
  │ TRAFFIC    │ how many req/s?              │ current load          │
  │ ERRORS     │ % of requests failing?      │ e.g. 100 fails/min    │
  │ SATURATION │ how full is the system?     │ only PREDICTIVE signal │
  └────────────┴──────────────────────────────┴───────────────────────┘
```

### Percentiles again (not averages)

```
  10,000 users complaining of slowness:
    AVERAGE = 332 µs   → "looks fine"     ❌
    P50     = 103 µs   → typical user
    P99     = 2,400 µs → the truth about your worst-hit 1%  ✔
```

> **SLOs are defined on P99 / P95 / P50 — never on the average.**

### ⚠ The cardinality trap

```
  LOW cardinality  (status code, region, env)   ──▶ OK in metrics ✔
  HIGH cardinality (user_id, request_id, order)  ──▶ NEVER in metrics ✖
                                                     put in logs + traces

  Rule of thumb: high-cardinality in metrics = slow monitoring + storage blowup
```

---

## Pillar 3 · TRACES — end-to-end record of ONE request

Each request gets a unique **trace ID** (a "tracking number") stitched across
every service it touches.

```
  trace_id: a1b2c3...
  FRONTEND ──▶ API GW ──▶ PAYMENT ──▶ DB QUERY
   ▇ 5ms       ▇ 8ms      ▇ 30ms      ▇▇▇▇▇▇▇▇ 795ms  ◀── bottleneck found!
                                       go straight to the DB — 100x faster debug
```

### Why traces matter — they crush MTTR

```
  WITHOUT TRACES                 WITH TRACES
  detect│■                       detect│■
  diag  │■■■■■■■■■■■■■■■■ (40m)   diag  │■■ (3m)  ← compressed
  fix   │■■■                     fix   │■■■  (same — depends on the code)
        └──────────────────▶            └──────────────────▶
  MTTR = mean time to repair / mitigation time
```

---

## Which signal answers which question?

```
  ┌─────────────────────────────────────────────┬──────────┐
  │ What exactly happened with order 5521?        │ LOGS     │
  │ How many orders failed in the last 10 min?    │ METRICS  │
  │ Which downstream service caused my downtime?  │ TRACES   │
  │ Is CPU creeping up over the last week?        │ METRICS  │
  │ Exact syntax error before the crash?          │ LOGS     │
  └─────────────────────────────────────────────┴──────────┘
```

## The unified workflow

```
  ① ALERT          ② TRACE                ③ LOG
  P99 latency      open trace ID,         read structured JSON
  spike fires  ─▶  find slow DB span  ─▶  on that span → exact error
  "something       "WHERE it's            "WHY it's broken"
   is broken"        broken"
```

---

## Key takeaways

1. **Logs** = what happened (discrete events). Prefer **structured JSON**.
2. **Metrics** = trends over time; watch the **4 golden signals**; use **percentiles**.
3. **Traces** = the journey of one request; pinpoint the bottleneck, crush MTTR.
4. Keep **high-cardinality** data out of metrics — put it in logs/traces.

**Next:** [03 · OpenTelemetry](03-opentelemetry.md)
