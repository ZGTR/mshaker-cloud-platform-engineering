# Day 16 — Resource Requests and Limits

> Video: Day 16/40 — Kubernetes Requests and Limits
> https://www.youtube.com/watch?v=Q-mk6EZVX_Q
> Duration: ~18 min

## Key terms
| Term | Meaning |
| --- | --- |
| Request | Guaranteed resources, used for scheduling |
| Limit | Hard ceiling on resource use |
| CPU | Compressible resource (throttled over its limit) |
| Memory | Incompressible resource (OOMKilled over its limit) |
| OOMKilled | Container killed for exceeding memory |
| QoS class | Guaranteed / Burstable / BestEffort |
| LimitRange | Default requests/limits per namespace |
| m / Mi | CPU millicores / memory mebibytes (units) |

## Problem & solution
Without resource declarations the scheduler can't place pods sensibly, and one
greedy container can starve or crash its neighbors on a node. Requests and
limits make resource use predictable and bounded.

**Solution:** Set requests (reserved, used for scheduling) and limits (hard ceiling, enforced at runtime) per container to share node capacity fairly.

## Where this fits in the cluster
Requests/limits are set per **container**. The **scheduler** uses requests to
pick a **node** with room; the kubelet/runtime enforces limits at runtime.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | scheduler  <== sums pod REQUESTS vs node free capacity         | |
   | +----------------------------------------------------------------+ |
   | +------- WORKER NODE   (kubelet | kube-proxy | runtime) --------+  |
   | | +------------------- namespace: default --------------------+ |  |
   | | | +------------------------- POD -------------------------+ | |  |
   | | | | +-------------------- CONTAINER --------------------+ | | |  |
   | | | | | app                                               | | | |  |
   | | | | |    <== requests = reserved; limits = hard ceiling | | | |  |
   | | | | +---------------------------------------------------+ | | |  |
   | | | +-------------------------------------------------------+ | |  |
   | | +-----------------------------------------------------------+ |  |
   | +---------------------------------------------------------------+  |
   +--------------------------------------------------------------------+
```

## The idea
- **Request** = the **guaranteed minimum** a container reserves. The scheduler
  uses it to pick a node with enough room.
- **Limit** = the **hard ceiling** a container may use at runtime.

```
   0 ......... request ......... limit ......... infinity
        scheduler reserves    container capped here
        this much for you
```

## CPU vs Memory behavior (IMPORTANT difference)
The two resources behave very differently when a container hits its limit: CPU is
**compressible** (throttled), memory is **not** (the container is killed).

```
   CPU over the limit    -> THROTTLED (slowed down, not killed)
   Memory over the limit -> OOMKilled (container killed, then restarted)
```

```
   Memory:  [====limit====]
            app tries to exceed -> X OOMKilled -> restart
   CPU:     [====limit====]
            app wants more -> ...throttled... (waits, keeps running)
```

## Deep dive: what happens when a pod needs more memory
This is the question that bites everyone in production. A container's memory
limit is a **cgroup ceiling fixed at container creation** — a running container
cannot simply "ask for more". What happens next depends on *whose* limit is hit
and how fast the app keeps allocating.

### First: the limit is set in stone while the container runs
You cannot grow a running container's memory limit by editing nothing. The
`limits.memory` value is baked into the container's cgroup when it starts.

```
   memory.limit = 256Mi   (cgroup ceiling, fixed at start)
   0 .............. usage grows .............. 256Mi |  X  (kernel says NO)
                                              app tries 257Mi -> denied/killed
```
To actually give it more memory you must **change the spec**, which (by default)
**recreates the pod** with the new limit. The old container is gone; a fresh one
starts with the bigger ceiling.

### Scenario A — growth STAYS under the limit (the happy path)
The app's working set rises but never crosses the ceiling. Nothing dramatic
happens; it just runs.

```
   limit 256Mi
   usage: 120Mi -> 180Mi -> 230Mi ........... (all < 256Mi)
   result: fine. no kill, no restart.
```

### Scenario B — usage CROSSES the container's own limit
The instant the container's processes try to allocate past the cgroup limit, the
**kernel OOM killer** kills a process inside that cgroup (usually PID 1, the main
process). The container exits with **code 137** (128 + SIGKILL) and the kubelet
restarts it per `restartPolicy`.

```
   limit 256Mi
   usage climbs ... 250Mi -> 256Mi -> tries 270Mi
                                        |
                                        v
                      kernel OOM killer fires inside the cgroup
                                        |
                                        v
            container EXITS 137 (OOMKilled)  ->  kubelet restarts it
```
Key point: this happens **even if the node has plenty of free RAM**. The
container hit *its own* limit, not the node's.

### What happens to the OTHER containers?
Each container has its **own** cgroup and its **own** limit. An OOMKill is
scoped to the offending container — siblings in the same pod and other pods on
the node keep running untouched.

```
   POD "web"
   +-----------------------------+------------------------------+
   | container: app  256Mi limit | container: sidecar 64Mi limit|
   | exceeds -> X OOMKilled       | unaffected -> keeps running  |
   | (restarts on its own)        |                              |
   +-----------------------------+------------------------------+
   RESTARTS column increments for "app" only, not for the whole pod.
```
(Exception: if the app container is the pod's reason to exist and keeps dying,
the *pod* is effectively down even though the sidecar is alive.)

### Scenario C — the NEW (bigger) limit is ALSO exhausted -> the crash loop
You raised the limit, redeployed... and the app eats that too (real leak, or it
genuinely needs more). Now you get the dreaded cycle:

```
   start -> allocate -> hit 512Mi limit -> OOMKilled (137) -> restart
     ^                                                          |
     +------------------------- repeat --------------------------+

   kubelet does NOT restart instantly forever — it backs off:
   restart #1: wait 10s   #2: 20s   #3: 40s   #4: 80s ... capped at 5 min
   STATUS shown to you:   CrashLoopBackOff
```
So **yes, it becomes a crash loop** — surfaced as `CrashLoopBackOff` with
**exponential backoff** (10s, 20s, 40s ... max 5 min) between restarts. Raising
the limit alone just buys a bigger number before the same loop returns.

### Scenario D — NODE runs out of memory (overcommit), not the container
Different failure entirely. If pods' **limits sum to more than the node's RAM**
(overcommit) and they all get busy, the *node* gets memory pressure. The kubelet
then **evicts** whole pods by QoS order — a container can die here while still
under its own limit.

```
   Node RAM: 4Gi   |   sum of limits: 6Gi  (overcommitted)
   pressure! kubelet evicts in this order:
        BestEffort  ->  Burstable (over its request)  ->  Guaranteed (last)
   This is EVICTION (pod removed/rescheduled), distinct from a per-container OOMKill.
```

```
   container hits ITS limit   -> kernel OOMKill -> container restarts in place
   NODE hits its capacity     -> kubelet EVICTS pods by QoS -> pod rescheduled
```

### How to actually solve it (not just raise the number)
Bumping the limit is only correct when the app *legitimately* needs more. Work
through this ladder:

```
   1. Is it a LEAK or real demand?
        kubectl top pod / metrics over time + heap profiling / dumps
        - flat-then-spike under load = real demand -> size for the peak
        - ever-climbing sawtooth     = leak       -> FIX the code, don't feed it
   2. Right-size the limit to the real peak (+ headroom), then redeploy.
   3. Set requests == limits  -> Guaranteed QoS -> survives node eviction longest.
   4. Make the runtime cgroup-aware so it respects the limit:
        JVM:   -XX:MaxRAMPercentage=75  (or -Xmx below the limit)
        Node:  --max-old-space-size  ;  Go: GOMEMLIMIT
   5. If it's load-driven, scale OUT (HPA, Day 17) instead of one giant pod.
   6. If it's per-pod growth, let VPA (Day 17) recommend/resize the limit.
   7. Newer clusters: in-place pod resize (InPlacePodVerticalScaling, 1.27+)
        can change limits WITHOUT recreating the pod.
   8. Stop the bleeding meanwhile: alert on restarts, and never let a leaky
        BestEffort pod threaten neighbors — give it requests/limits.
```

> Mental model: **OOMKill is a symptom, not the disease.** A bigger limit moves
> the wall further out; a leak just walks to the new wall. Profile first, size
> second, scale third.

## Units
CPU is measured in cores or **millicores**, and memory in binary (`Mi`/`Gi`) or
decimal (`M`/`G`) byte units.

```
   CPU:    1 = 1 vCPU core ;  500m = 0.5 core (m = millicores)
   Memory: Mi = mebibyte (1024-based), M = megabyte (1000-based)
           128Mi, 256Mi, 1Gi ...
```

## YAML
Requests and limits are declared per container under `resources`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: app
      image: nginx
      resources:
        requests:
          cpu: "250m"
          memory: "128Mi"
        limits:
          cpu: "500m"
          memory: "256Mi"
```

## How scheduling uses requests
The scheduler places pods based on their **requests** versus a node's free
capacity — not on actual live usage.

```
   Node capacity: 2 CPU
   Existing requests: 1.5 CPU used
   New pod requests: 0.75 CPU
   1.5 + 0.75 = 2.25 > 2  -> won't fit -> Pending
   (Scheduling is based on REQUESTS, not actual usage.)
```

## QoS classes (derived from requests/limits)
Kubernetes assigns each pod a **Quality of Service** class from how its requests
and limits are set, which decides eviction priority under pressure.

```
   Guaranteed  -> requests == limits for every resource (highest priority)
   Burstable   -> has requests < limits                (medium)
   BestEffort  -> no requests or limits set            (first to be evicted)
```
```bash
kubectl get pod app -o jsonpath='{.status.qosClass}{"\n"}'
```
Under node memory pressure, eviction order: **BestEffort -> Burstable -> Guaranteed**.

## LimitRange — defaults per namespace
A **LimitRange** injects default requests and limits for any container in a
namespace that doesn't specify its own.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: dev
spec:
  limits:
    - default:            # default LIMIT if not set
        cpu: 500m
        memory: 256Mi
      defaultRequest:     # default REQUEST if not set
        cpu: 250m
        memory: 128Mi
      type: Container
```

## Inspect usage
Commands to view a pod's configured resources and its live consumption.

```bash
kubectl describe pod app                    # see Requests/Limits + events
kubectl top pod                             # live usage (needs metrics-server)
kubectl top node
kubectl get events --field-selector reason=OOMKilling
# diagnosing an OOM crash loop:
kubectl get pod app                                         # STATUS CrashLoopBackOff, RESTARTS climbing
kubectl describe pod app | grep -A3 'Last State'            # Reason: OOMKilled, Exit Code: 137
kubectl get pod app -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'  # 137
kubectl logs app --previous                                 # logs of the killed (previous) container
```

## End-to-end example: see scheduling + QoS + OOMKill
Deploy a Guaranteed pod, confirm its QoS class, then force an OOMKill by asking
for more memory than its limit allows.

```
   requests == limits  ->  QoS: Guaranteed
   app allocates 300Mi with a 256Mi limit  ->  X OOMKilled -> restart
```

```yaml
apiVersion: v1
kind: Pod
metadata: { name: mem-demo }
spec:
  containers:
    - name: app
      image: polinux/stress
      resources:
        requests: { cpu: "250m", memory: "256Mi" }
        limits:   { cpu: "250m", memory: "256Mi" }   # == requests -> Guaranteed
      command: ["stress"]
      args: ["--vm", "1", "--vm-bytes", "300M", "--vm-hang", "1"]   # > 256Mi
```

```bash
kubectl apply -f mem-demo.yaml
kubectl get pod mem-demo -o jsonpath='{.status.qosClass}{"\n"}'   # Guaranteed
kubectl get pod mem-demo                       # RESTARTS climbs as it OOMKills
kubectl describe pod mem-demo | grep -A2 'Last State'   # Reason: OOMKilled
kubectl get events --field-selector reason=OOMKilling
```

## Key takeaways
- **Request = reserved/scheduled; Limit = max allowed.**
- Over-limit: **CPU throttles, Memory gets OOMKilled**.
- requests==limits -> **Guaranteed** QoS; nothing set -> **BestEffort** (evicted first).

## Checklist
- [ ] Set requests/limits on a pod
- [ ] Triggered an OOMKill by exceeding the memory limit
- [ ] Saw it become `CrashLoopBackOff` (exit 137) when it kept exceeding
- [ ] Confirmed an OOMKill restarts only the offending container, not siblings
- [ ] Can explain per-container OOMKill vs node-pressure eviction
- [ ] Checked the pod's QoS class
- [ ] Used `kubectl top` (with metrics-server) and a LimitRange
