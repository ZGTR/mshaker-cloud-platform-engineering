# Day 16 — Resource Requests and Limits

> Video: Day 16/40 — Kubernetes Requests and Limits
> https://www.youtube.com/watch?v=Q-mk6EZVX_Q
> Duration: ~18 min

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
```

## Key takeaways
- **Request = reserved/scheduled; Limit = max allowed.**
- Over-limit: **CPU throttles, Memory gets OOMKilled**.
- requests==limits -> **Guaranteed** QoS; nothing set -> **BestEffort** (evicted first).

## Checklist
- [ ] Set requests/limits on a pod
- [ ] Triggered an OOMKill by exceeding the memory limit
- [ ] Checked the pod's QoS class
- [ ] Used `kubectl top` (with metrics-server) and a LimitRange
