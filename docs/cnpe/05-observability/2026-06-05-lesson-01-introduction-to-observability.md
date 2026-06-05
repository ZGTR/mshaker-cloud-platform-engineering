# 01 · Introduction to Observability — Monitoring vs Observability

- **Video:** <https://www.youtube.com/watch?v=_Gj6eSCFWts>
- **Length:** 21:54 · **Type:** Theory

> **What you'll learn**
> - The difference between **monitoring** and **observability**
> - Why "all green dashboards" still leave users complaining
> - **P50 / P95 / P99** latency and why averages lie
> - Knowns vs unknowns, and the 3 core properties of an observable system

---

## 1. Monitoring in one line

> Monitoring = collecting and watching **predefined** signals, comparing them to
> **thresholds**, and firing an **alert** (a "page") when a line is crossed.

```
   METRICS (predefined)        THRESHOLD            ACTION
   ┌──────────────┐         ┌────────────┐       ┌──────────────┐
   │ CPU   85%    │ ─────▶  │ CPU  > 80% │ ───▶  │ TRIGGER PAGE │
   │ MEM   70%    │         │ MEM  > 75% │       │ (alert/beep) │
   │ DISK  60%    │         │ 5xx  > 100 │       └──────────────┘
   │ HTTP 5xx     │         └────────────┘
   └──────────────┘
```

> "Page" comes from the old **pager/beeper** — still used in SRE/DevOps slang
> for any alert (phone, email, notification).

**The catch:** monitoring tells you *WHEN* something is wrong, never *WHY*.

---

## 2. Why monitoring breaks in modern systems

```
   MONOLITH (old)                  MICROSERVICES (today)
   ┌───────────────┐                  ●───●───●
   │  ONE server   │                 ╱│   │   │╲
   │  CPU/MEM/DISK │                ● ●───●───● ●
   │  ~10 things   │                 ╲│   │   │╱
   │  can break    │                  ●───●───●
   └───────────────┘              thousands of failure modes,
   easy to monitor                many never seen before
```

You **cannot write a predefined alert for a failure you haven't invented yet.**

### The silent failure

```
 USER ─▶ FRONTEND ─▶ API GW ─▶ ORDER ─▶ PAYMENT ─▶ DB
  ▲                                        │  expected:  80 µs
  └──────────── slow response ─────────────┘  actual:    800 µs  ⚠ SLOW
                                              (not failing — just slow!)
```

Everything is "green" because you watched **error rate**, not **P99 latency**.
The service isn't down; it's slow — and the alert is blind to it.

---

## 3. Averages lie — use percentiles

```
   1,000,000 users, only ~1% are suffering
   AVERAGE  ──▶ buried, looks fine ❌
                                          slowest
   P50 ─────────────────────────┐      (the truth)
   P95 ─────────────────────────────────┐  │
   P99 ─────────────────────────────────────┐
   │       │                              │  │
   0%     50%        95%   99% ───────────┴──┴─▶ latency
```

| Percentile | Meaning | Who it represents |
|-----------|---------|-------------------|
| **P50** (median) | 50% of requests are faster | typical experience |
| **P95** | 95% faster | 1 in 20 unlucky users |
| **P99** | 99% faster | worst-hit **1%** — the complainers |

> **P99** = average latency *of the slowest 1%*. That's where the real problem
> hides. The average over all users hides it.

---

## 4. Knowns & Unknowns (the monitoring gap)

```
                 │ KNOWN cause          │ UNKNOWN cause
   ──────────────┼──────────────────────┼─────────────────────────
   KNOWN to ask  │ CPU/MEM checks        │ "we have data but
                 │  ✔ solved by          │  ignore it"
                 │    MONITORING         │
   ──────────────┼──────────────────────┼─────────────────────────
   UNKNOWN to ask│ data exists,          │ NEVER anticipated, e.g.
                 │ overlooked            │ missing DB index ⇒
                 │                       │ cascading latency
                 │                       │  ◀── THE GAP
                 │                       │      OBSERVABILITY
```

> Observability term coined in **1960s by Rudolf Kálmán** (control theory):
> *a system is observable if you can understand its internal state purely from
> its external output.*

---

## 5. Observability does the diagnosis for you

```
 USER ─▶ FRONTEND ─▶ API GW ─▶ PAYMENT(812µs) ─▶ PAYMENT-DB(780µs) ◀ bottleneck
        every hop emits a timestamped, end-to-end record (trace)
        total 820µs  ─  you SEE the 780µs DB span ─ go straight to the DB
```

No SSH, no grep, no redeploy — the rich telemetry already points at the cause
(e.g. a missing index).

---

## 6. The 3 core properties of an observable system

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. HIGH CARDINALITY   drill down to ONE specific request │
  │ 2. HIGH DIMENSIONALITY slice/filter by endless attributes│
  │ 3. HYPOTHESIS-FREE     ask new questions in real time,   │
  │    EXPLORATION         no redeploy                       │
  └────────────────────────────────────────────────────────┘
   Have all 3 → observable.   Missing them → you're guessing.
```

- **High cardinality** — every request carries `user_id`, `request_id`,
  `trace_id`, timestamp, error code, labels…
- **High dimensionality** — filter by region, service, DB host, user tier,
  feature flag, tags…

---

## 7. Litmus test — are you actually observable?

```
  Q1  User reports failure → can you find the EXACT request,
      or only an error count?            count → ❌ monitoring trap
  Q2  Alert fires → do you already have the data,
      or must you SSH + grep logs?       ssh  → ❌ monitoring trap
  Q3  Did you add a NEW metric AFTER an incident
      because you realised you needed it? yes → ❌ monitoring trap
```

---

## Monitoring vs Observability — cheat sheet

| | Monitoring | Observability |
|---|-----------|---------------|
| Question | *Is it broken?* | *Why is it broken?* |
| Scope | knowns + knowns | unknown-unknowns |
| Data | aggregates, averages, counts | rich, granular, high-context events |
| New metric | **redeploy** to add | **query** existing data live |

---

## Key takeaways

1. Monitoring watches predefined signals — tells you **when**, hides the **why**.
2. Observability needs **rich structured telemetry** (high cardinality + dimensionality) to diagnose **unknown** failures.
3. The real difference isn't the tool — it's the **data underneath**. Better tooling on poor telemetry just gives you a faster dashboard showing the wrong thing.

**Next:** [02 · Logs, Metrics & Traces](02-logs-metrics-traces.md)
