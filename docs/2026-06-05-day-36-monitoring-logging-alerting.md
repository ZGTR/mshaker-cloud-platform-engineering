# Day 36 — Monitoring, Logging, and Alerting

> Video: Day 36/40 — Monitoring, Logging and Alerting
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| Metrics | Numeric time-series (CPU, memory, latency) |
| Logs | Event records from apps and components |
| Alerting | Notify when thresholds are breached |
| metrics-server | Built-in resource metrics source |
| Prometheus | Metrics collection and storage |
| Grafana | Dashboards and visualization |
| Alertmanager | Routes and dedupes alerts |

## Problem & solution
A cluster you can't see is a cluster you can't operate. You need three distinct
signals: **metrics** (numbers over time — CPU, memory, request rate), **logs**
(what each app printed), and **alerts** (be told when something is wrong before
users notice). Each answers a different question.

**Solution:** Collect metrics (Prometheus/metrics-server), ship logs (stdout to an agent to Loki/ELK), and route alerts (Alertmanager) on user-visible symptoms.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------- CLUSTER -------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+    |
   | | +------------+   +------+   +-----------+   +----------------+ |    |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |    |
   | | +------------+   +------+   +-----------+   +----------------+ |    |
   | | controller-mgr  <== metrics-server feeds HPA + 'kubectl top'   |    |
   | +----------------------------------------------------------------+    |
   | +--------- WORKER NODE   (kubelet | kube-proxy | runtime) ----------+ |
   | |    <== kubelet/cAdvisor expose node + pod metrics; logs live here | |
   | | + namespace: default +                                            | |
   | | | +----- POD -----+  |                                            | |
   | | | | + CONTAINER + |  |                                            | |
   | | | | | app       | |  |                                            | |
   | | | | +-----------+ |  |                                            | |
   | | | +---------------+  |                                            | |
   | | +--------------------+                                            | |
   | +-------------------------------------------------------------------+ |
   +-----------------------------------------------------------------------+
```

## Three signals, three jobs
```
   METRICS  numbers over time     "CPU is 90%, p99 latency is 800ms"   -> Prometheus
   LOGS     discrete events       "NullPointerException at 12:04"      -> Loki/ELK
   ALERTS   notify on a condition "fire if 5xx > 1% for 5m"            -> Alertmanager
```

## metrics-server (the built-in baseline)
`metrics-server` scrapes the kubelet (cAdvisor) for live CPU/memory and powers
`kubectl top` and the **HPA** (Day 17). It is **not** long-term storage.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl top nodes                 # live node CPU/memory
kubectl top pods -A               # live pod CPU/memory
```
> On kubeadm/kind you often need `--kubelet-insecure-tls` on the metrics-server
> args (self-signed kubelet certs).

## Metrics pipeline (Prometheus + Grafana)
For history, dashboards, and alerts, the standard stack is **Prometheus**
(scrape + store + alert rules), **Alertmanager** (route/notify), and **Grafana**
(dashboards). Install via the `kube-prometheus-stack` Helm chart.

```
   targets (kubelet, node-exporter, app /metrics, kube-state-metrics)
        --scrape--> Prometheus --store--> TSDB
                         |  \
                  alert rules \--> Alertmanager --> Slack / PagerDuty / email
                         |
                      Grafana (dashboards + queries)
```

## Logging
Containers should log to **stdout/stderr**; the runtime writes them to the node,
and `kubectl logs` reads them. For retention and search, a node agent ships logs
to a backend.

```bash
kubectl logs <pod>                       # current logs
kubectl logs <pod> -c <container>        # a specific container
kubectl logs <pod> --previous            # the crashed instance's logs
kubectl logs -f deploy/api --tail=100    # follow a Deployment
```
```
   app -> stdout/stderr -> /var/log/containers/*.log (node)
        -> DaemonSet agent (Fluent Bit / Promtail / Vector)
        -> Loki / Elasticsearch / cloud logging  (search + retention)
```
> Don't log to files inside the container — they vanish with the pod and can't be
> collected. stdout/stderr is the contract.

## Alerting that's actually useful
Alert on **symptoms users feel**, not every blip. Classic starting points:

```
   - high error rate     5xx ratio > 1% for 5m
   - latency             p99 > 1s for 10m
   - pod health          CrashLoopBackOff / not Ready > 5m
   - node pressure       MemoryPressure / DiskPressure
   - capacity            PVC > 85% full; node CPU/mem saturated
   - control plane       apiserver/etcd down, certs expiring < 7d
```

## Key takeaways
- Three signals: **metrics** (Prometheus), **logs** (Loki/ELK), **alerts** (Alertmanager).
- **metrics-server** powers `kubectl top` + HPA, but is **not** storage.
- Apps log to **stdout/stderr**; a DaemonSet agent ships them off-node.
- `kubectl logs --previous` recovers a crashed container's last words.
- Alert on **user-visible symptoms**, with sane durations to avoid noise.

## Checklist
- [ ] Installed metrics-server; `kubectl top nodes/pods` works
- [ ] Can name the role of Prometheus, Grafana, and Alertmanager
- [ ] Read current and `--previous` logs for a pod
- [ ] Explained the stdout -> node -> agent -> backend log pipeline
- [ ] Listed 3+ symptom-based alerts worth configuring
