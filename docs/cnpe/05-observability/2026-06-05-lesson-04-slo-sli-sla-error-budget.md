# 04 · SLI vs SLO vs SLA + Error Budget (Google SRE)

- **Video:** <https://www.youtube.com/watch?v=Akri1BlGp10>
- **Length:** 19:15 · **Type:** Theory

> **What you'll learn**
> - Plain-English definitions of **SLI**, **SLO**, **SLA**
> - How they nest, and who owns each
> - **Error budget** and how it drives ship-vs-freeze decisions
> - Why **100% uptime is dangerous** (Google's Chubby lesson)

---

## 1. The one-screen mental model

```
              ┌──────────────────────────────────────────┐
              │  SLA  — contract w/ customer (legal)      │  ← outer ring
              │  "miss it ⇒ we owe you money"             │
              │   ┌────────────────────────────────────┐ │
              │   │ SLO — internal target (good enough) │ │
              │   │   ┌──────────────────────────────┐  │ │
              │   │   │ SLI — what the service IS     │  │ │  ← inner ring
              │   │   │ doing RIGHT NOW (measurement) │  │ │
              │   │   └──────────────────────────────┘  │ │
              │   └────────────────────────────────────┘ │
              └──────────────────────────────────────────┘
  Build inside-out: you must MEASURE (SLI) → set a TARGET (SLO) → promise (SLA)
```

---

## 2. The three terms (car analogy)

```
  ┌──────┬────────────────────────┬─────────────────────────┬───────────────┐
  │      │ Plain English          │ Car analogy             │ Owned by      │
  ├──────┼────────────────────────┼─────────────────────────┼───────────────┤
  │ SLI  │ what the service is    │ "going 60 mph right now"│ Engineering / │
  │      │ DOING right now        │                         │ SRE           │
  ├──────┼────────────────────────┼─────────────────────────┼───────────────┤
  │ SLO  │ what GOOD ENOUGH       │ "speed limit ≤ 65 mph"  │ Product / SRE │
  │      │ looks like (target)    │                         │               │
  ├──────┼────────────────────────┼─────────────────────────┼───────────────┤
  │ SLA  │ what happens IF WE MISS│ "90 in an 80 zone =     │ Business /    │
  │      │ (contract + penalty)   │  $150 ticket"           │ Legal         │
  └──────┴────────────────────────┴─────────────────────────┴───────────────┘
```

**The one-liner test:** *"What happens if we miss the target?"*
- *"Nothing formal"* → it's an **SLO**.
- *"We owe the customer money"* → it's an **SLA**.

---

## 3. Worked example (AWS EC2-style)

```
  SLI  →  % of requests returning HTTP 200        (the raw fact, measured now)
  SLO  →  99.99% uptime                            (internal target)
  SLA  →  99.9% uptime, else 10% service credit     (contract w/ customer)
                                   ▲
                buffer between SLO (99.99) and SLA (99.9) protects you
```

### Picking an SLI

```
  user-facing / API / frontend ──▶ availability, latency, throughput
  backend / data / storage     ──▶ availability, latency, durability

  Heuristic: "If the service broke today, what would users be tweeting about?"
             → that is your SLI.
```

---

## 4. Why percentiles, not averages (again)

```
  AVERAGE latency line:  ───────────────  looks healthy ❌
  (1% of users are in pain, but the average drowns them out)

  P50 = typical    P95 = unlucky 5%    P99 = worst 1% (e.g. 30s timeouts!)
  ⇒ Always graph/alert on P99 / P95 / P50 — never the average.
```

---

## 5. Error budget — your "operational data plan"

```
   100%  ┌──────────────────────────────────────────┐
         │            ERROR BUDGET                    │  100% − SLO
         │            (0.1% ≈ 8.7 h / year)           │
   SLO ──┼────────────────────────────────────────────┤  e.g. 99.9%
         │                                            │
         │            normal operation                │
    0%   └──────────────────────────────────────────┘
```

```
  Budget LEFT  ──▶ experiment, ship faster, take risks 🚀
  Budget SPENT ──▶ freeze releases, slow down, stabilise 🧊
                   (also common around holidays / quarter-end)
```

> Error budget = `100% − SLO`. With 99.9% SLO you may "spend" ~**8.7 hours** of
> downtime per year. It's a budget to *play with*, not a target to burn.

---

## 6. Why 100% uptime is dangerous — Google's Chubby

```
   Aiming for 100% ⇒ false sense of security
   ─────────────────────────────────────────
   Real outage hits ──▶ dependent services have NO fallback ──▶ CASCADING FAILURE

   Google's fix: deliberately take down "Chubby" (distributed lock service)
   once per quarter  →  chaos engineering  →  dependents learn resiliency.
```

> Never promise 100%. Even AWS S3 advertises 99.99…9% — a sliver is always
> reserved for reality.

---

## 7. The SRE operational loop

```
   ┌─▶ READ SLI ──▶ COMPARE to SLO ──▶ CHECK error budget ──▶ ACT ──┐
   │   (measure)     (are we ok?)        (how much left?)     │      │
   │                                                          ▼      │
   │                                   ship faster │ freeze │ protect SLA
   └──────────────────────────────── continuous loop ───────────────┘
```

---

## Key takeaways

1. **SLI** = what you *measure*. **SLO** = the *target*. **SLA** = the *contract* (penalty if missed).
2. Build **inside-out**: SLI → SLO → SLA. You can't promise what you don't measure.
3. **Error budget = 100% − SLO**; it governs the ship-vs-freeze "brake pedal".
4. Never target 100% — engineer for realistic reliability and practice failure.

**Next:** [05 · Honeycomb + Kubernetes Project](05-honeycomb-k8s-project.md)
