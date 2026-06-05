# Day 17 — Autoscaling: HPA vs VPA

> Video: Day 17/40 — Kubernetes Autoscaling Explained | HPA vs VPA
> https://www.youtube.com/watch?v=afUL5jGoLx0
> Duration: ~26 min

## Two directions of scaling
Autoscaling works along two axes: **horizontal** (run more pods) and **vertical**
(give each pod more CPU/memory).

```
   HPA (Horizontal) -> MORE pods         VPA (Vertical) -> BIGGER pods
   +---+            +---+ +---+ +---+     +---+              +-------+
   |pod|   ---->    |pod| |pod| |pod|     |pod|    ---->     |  POD  |
   +---+            +---+ +---+ +---+     +---+              +-------+
   add replicas                          add CPU/memory to each pod
```

There is also the **Cluster Autoscaler** (adds/removes *nodes*) — different layer.

```
   Cluster Autoscaler -> scale NODES
   HPA                -> scale POD COUNT
   VPA                -> scale POD SIZE (requests/limits)
```

## Prerequisite: metrics-server
Both read live metrics from the **metrics-server**.
```bash
kubectl top pod      # must work first
kubectl top node
```

## HPA — Horizontal Pod Autoscaler
The **HPA** watches a metric (commonly average CPU) and adds or removes replicas
to keep it near a target, within min/max bounds.

```
   measure avg CPU across pods
        |
        v
   utilization > target?  -> add replicas (up to max)
   utilization < target?  -> remove replicas (down to min)
```

```bash
# imperative
kubectl autoscale deployment web --cpu-percent=50 --min=2 --max=10
kubectl get hpa
kubectl describe hpa web
```

HPA YAML (autoscaling/v2):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50      # target 50% of the CPU REQUEST
```

> HPA percentage is relative to the pod's CPU **request** (Day 16) — so requests
> must be set for HPA to work.

## Generate load to watch it scale
Drive traffic at the service to push CPU up and watch the HPA add replicas.

```bash
kubectl run load --image=busybox -it --rm -- \
  sh -c "while true; do wget -q -O- http://web; done"
kubectl get hpa web --watch        # see replicas climb, then settle
```

## VPA — Vertical Pod Autoscaler
The **VPA** observes real usage over time and right-sizes a pod's requests and
limits, recreating the pod to apply the new size.

```
   observes actual usage over time
        |
        v
   recommends / sets better requests & limits
        |
        v
   pods are RECREATED with the new size (brief restart)
```
- Not built-in by default; install the VPA component separately.
- Modes: `Off` (recommend only), `Auto`/`Recreate` (apply by restarting pods).

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: web
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  updatePolicy:
    updateMode: "Auto"
```

## HPA vs VPA
A side-by-side of when each scaler fits and the trade-offs between them.

| | HPA | VPA |
|---|-----|-----|
| Scales | number of pods | size of pods (req/limits) |
| Disruption | none (adds/removes) | restarts pods to resize |
| Best for | stateless, spiky traffic | right-sizing, stateful-ish |
| Built-in | yes | install separately |

> Don't run HPA and VPA on the **same CPU/memory metric** at once — they fight.

## Key takeaways
- **HPA = more pods; VPA = bigger pods; Cluster Autoscaler = more nodes.**
- Both need **metrics-server**; HPA targets a % of the CPU **request**.
- VPA resizes by **recreating** pods; avoid overlapping HPA+VPA on same metric.

## Checklist
- [ ] Confirmed `kubectl top` works (metrics-server)
- [ ] Created an HPA and watched replicas scale under load
- [ ] Understand VPA recreates pods to resize them
- [ ] Can explain HPA vs VPA vs Cluster Autoscaler
