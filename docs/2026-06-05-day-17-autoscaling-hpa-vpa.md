# Day 17 — Autoscaling: HPA vs VPA

> Video: Day 17/40 — Kubernetes Autoscaling Explained | HPA vs VPA
> https://www.youtube.com/watch?v=afUL5jGoLx0
> Duration: ~26 min

## Key terms
| Term | Meaning |
| --- | --- |
| HPA | Horizontal Pod Autoscaler — scales the replica count |
| VPA | Vertical Pod Autoscaler — adjusts requests/limits |
| metrics-server | Supplies CPU/memory usage to autoscalers |
| Target utilization | Metric threshold that triggers scaling |
| Scale out/in | Add / remove pods |
| Replica | One pod copy |

## Problem & solution
Static replica counts and fixed pod sizes either waste money at low traffic or
fall over under spikes. Capacity (pod count and pod size) needs to track real
demand automatically.

**Solution:** Scale pod count with the HPA and right-size pods with the VPA, fed by metrics-server, and add the Cluster Autoscaler for nodes.

## Where this fits in the cluster
Each autoscaler acts at a different layer: **HPA** changes pod count, **VPA**
changes pod size, **Cluster Autoscaler** adds/removes nodes. All read the
metrics-server.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | controller-mgr  <== HPA / VPA controllers + metrics-server     | |
   | +----------------------------------------------------------------+ |
   | +----- WORKER NODE   (kubelet | kube-proxy | runtime) ------+      |
   | | +----------------- namespace: default ------------------+ |      |
   | | | +----------------------- POD -----------------------+ | |      |
   | | | | +------------------ CONTAINER ------------------+ | | |      |
   | | | | | app                                           | | | |      |
   | | | | |    <== VPA changes the SIZE (requests/limits) | | | |      |
   | | | | +-----------------------------------------------+ | | |      |
   | | | |    <== HPA changes the NUMBER of pods             | | |      |
   | | | +---------------------------------------------------+ | |      |
   | | +-------------------------------------------------------+ |      |
   | +-----------------------------------------------------------+      |
   +--------------------------------------------------------------------+
```

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

## Scaling DOWN: what happens as CPU recedes
Scaling up is eager; scaling **down is deliberately slow and cautious** to avoid
"flapping" (thrashing pods/nodes up and down). Two layers wind down in order:
first the **HPA removes pods**, then the **Cluster Autoscaler removes the now
empty nodes**.

```
   load fades -> avg CPU drops -> HPA removes pods -> nodes empty out
                                                   -> Cluster Autoscaler
                                                      drains + deletes nodes
```

### The math HPA uses (up AND down)
The HPA recomputes a target replica count every ~15s with one formula. The same
formula that scales up also scales down.

```
   desiredReplicas = ceil[ currentReplicas x (currentCPU / targetCPU) ]

   scale-down example:  8 pods, avg CPU 12%, target 50%
   desired = ceil(8 x 12/50) = ceil(1.92) = 2  -> shrink 8 -> 2 (min)
```

### Guardrail 1 — the tolerance band (no action near target)
If current utilization is within ~10% of target, the HPA does **nothing**. This
stops tiny wiggles from constantly resizing.

```
   target 50%   ->  tolerance band 45% .. 55%
   45% ----------------[ 50 ]---------------- 55%
        |  inside the band -> NO scale up/down  |
   only readings OUTSIDE the band trigger a change.
```

### Guardrail 2 — the scale-down stabilization window (the big one)
Before removing pods, the HPA looks back over a **stabilization window
(default 300s = 5 min)** and uses the **highest** desired count seen in that
window. So a brief dip won't immediately shed pods — CPU must stay low for ~5
minutes before pods actually go away.

```
   CPU drops at t0, but HPA waits and watches:
   t0 .... t1 .... t2 .... t3 .... t4 .... t5min
   desired: 8      4       2       2       2       2
            |__ over the last 5 min the MAX desired is used __|
   -> only after CPU is low for the whole window does it settle to 2
   (scale-UP has a 0s window by default -> reacts fast; DOWN is slow on purpose)
```

### Scenario 1 — traffic tapers off (typical evening drop)
Peak is over, requests fall, CPU per pod sinks well below target. HPA waits out
the window, then steps the replica count down toward `minReplicas`.

```
   PEAK:  8 pods @ ~50% CPU  (at target)
   traffic falls -> 8 pods @ ~12% CPU
   wait 5 min (stabilization) ...
   HPA: 8 -> 2 pods   (never below minReplicas: 2)
```

### Scenario 2 — a short dip, then load returns (flap prevention)
CPU dips for 90s then climbs back. Because the dip is shorter than the 5-min
window, the HPA holds the higher count and **never removes** the pods — exactly
what we want.

```
   CPU: 50% -> 15% (90s) -> 55%
   window (300s) still "remembers" the high desired -> replicas held
   result: no needless scale-down, no flap.
```

### Scenario 3 — pods left, now NODES are underutilized
Once the HPA has shed pods, nodes may sit nearly empty. The **Cluster
Autoscaler** (cloud clusters) notices a node whose **requested** resources are
low and whose pods can fit elsewhere, then cordons, drains, and deletes it.

```
   after HPA scale-down: 2 pods total, spread thin
   node-A [pod]   node-B [pod]   node-C [ empty ]
        |              |
        +--- CA: pods fit on fewer nodes? reschedule + remove spare nodes
   node-C unneeded for ~10 min (scale-down-unneeded-time)
        -> cordon -> drain (evict pods, honor PodDisruptionBudgets) -> delete node
   typical CA trigger: node's total REQUESTS < ~50% of allocatable, sustained.
```

> Two different signals: HPA scales on **live CPU usage**; Cluster Autoscaler
> scales on **scheduled requests** + whether pods can be packed elsewhere.

### Scenario 4 — a node REFUSES to scale down (and how to fix it)
Often a node lingers because one pod on it blocks eviction. The Cluster
Autoscaler will not remove a node if draining it is unsafe.

```
   Blockers that pin a node up:
     - a pod with NO controller (bare pod)            -> can't be safely moved
     - kube-system pod without a PodDisruptionBudget  -> drain blocked
     - pod using local storage / emptyDir it can't lose
     - restrictive PodDisruptionBudget (minAvailable too high)
     - annotation: cluster-autoscaler.kubernetes.io/safe-to-evict: "false"

   Fixes: run replicated workloads (Deployment), add sane PDBs, avoid local
   storage for movable pods, drop the safe-to-evict=false annotation.
```

### Tune the scale-down behavior (autoscaling/v2)
The `behavior.scaleDown` block lets you make shrink slower/faster and cap how
many pods leave per step. Useful to protect warm caches or connection pools.

```yaml
spec:
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300     # wait 5 min of low load before shrinking
      policies:
        - type: Percent                   # remove at most 50% of pods ...
          value: 50
          periodSeconds: 60               # ... per 60s
        - type: Pods                      # and never more than 2 pods ...
          value: 2
          periodSeconds: 60
      selectPolicy: Min                   # pick the most conservative policy
    scaleUp:
      stabilizationWindowSeconds: 0       # scale up immediately
```

```bash
kubectl get hpa web --watch        # watch REPLICAS step DOWN after load stops
kubectl describe hpa web           # events: "New size: 2; reason: All metrics below target"
kubectl get events | grep -i 'scaledown\|ScalingReplicaSet'
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

## End-to-end example: deploy, autoscale, load-test
Deploy a CPU-bound web app with **requests set** (HPA needs them), attach an HPA,
then drive load and watch replicas climb and settle.

```
   load up   -> avg CPU 80% > target 50%  -> HPA adds pods (2 -> ... -> 10)
   load gone -> avg CPU low               -> HPA removes pods (back to 2)
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: web }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: web
          image: registry.k8s.io/hpa-example
          ports: [{ containerPort: 80 }]
          resources:
            requests: { cpu: "200m" }      # REQUIRED for HPA's % math
            limits:   { cpu: "500m" }
---
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  selector: { app: web }
  ports: [{ port: 80 }]
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: web }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: web }
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 50 } }
```

```bash
kubectl apply -f web-hpa.yaml
kubectl top pod                              # confirm metrics-server works
# generate load in another terminal:
kubectl run load --image=busybox -it --rm -- \
  sh -c "while true; do wget -q -O- http://web; done"
kubectl get hpa web --watch                  # TARGETS climbs, REPLICAS scale up
```

## Key takeaways
- **HPA = more pods; VPA = bigger pods; Cluster Autoscaler = more nodes.**
- Both need **metrics-server**; HPA targets a % of the CPU **request**.
- **Scale-up is fast; scale-down is slow on purpose** — a 5-min stabilization
  window + 10% tolerance band prevent flapping.
- HPA sheds pods on **live CPU**; Cluster Autoscaler removes nodes on **low
  requests + reschedulable pods**, after a sustained unneeded period.
- A single un-evictable pod (bare pod, strict PDB, local storage) can **block**
  a node from scaling down.
- VPA resizes by **recreating** pods; avoid overlapping HPA+VPA on same metric.

## Checklist
- [ ] Confirmed `kubectl top` works (metrics-server)
- [ ] Created an HPA and watched replicas scale under load
- [ ] Watched replicas step DOWN after load stops (and timed the ~5-min wait)
- [ ] Explained why a short dip does NOT trigger scale-down (stabilization window)
- [ ] Tuned `behavior.scaleDown` policies on an HPA
- [ ] Understand how Cluster Autoscaler drains + removes underutilized nodes
- [ ] Understand VPA recreates pods to resize them
- [ ] Can explain HPA vs VPA vs Cluster Autoscaler
