# Day 18 — Health Probes: Liveness vs Readiness (vs Startup)

> Video: Day 18/40 — Kubernetes Health Probes | Liveness vs Readiness Probes
> https://www.youtube.com/watch?v=x2e6pIBLKzw
> Duration: ~29 min

## Why probes?
A container can be **running but broken** (deadlocked) or **not yet ready** (still
warming up). Probes let the kubelet check actual health and react.

## The three probes

```
   Liveness   -> "Is it alive?"     fail -> RESTART the container
   Readiness  -> "Can it serve?"    fail -> remove from Service endpoints
   Startup    -> "Has it booted?"   fail -> kill; gates the other two
```

```
   Readiness FAIL:
   Service --x--> [pod]      (pod kept running, just gets NO traffic)
   Liveness FAIL:
   kubelet kills + restarts [pod]
```

## Liveness vs Readiness (the key distinction)
```
   Readiness controls TRAFFIC   (in/out of the load balancer)
   Liveness   controls LIFECYCLE (restart the container)
```
A pod can be **Live but not Ready** (alive, still warming up -> no traffic yet).

## Probe types (how the check is done)
```
   httpGet   -> GET a path/port; 2xx-3xx = pass
   tcpSocket -> can we open the TCP port? = pass
   exec      -> run a command in container; exit 0 = pass
```

## YAML — all three
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: app
      image: myapp:1.0
      ports:
        - containerPort: 8080
      startupProbe:                # gate slow starters first
        httpGet: { path: /healthz, port: 8080 }
        failureThreshold: 30
        periodSeconds: 10          # allows up to 300s to boot
      readinessProbe:
        httpGet: { path: /ready, port: 8080 }
        initialDelaySeconds: 5
        periodSeconds: 10
      livenessProbe:
        httpGet: { path: /healthz, port: 8080 }
        initialDelaySeconds: 10
        periodSeconds: 10
```

## tcpSocket and exec variants
```yaml
      readinessProbe:
        tcpSocket: { port: 5432 }
      livenessProbe:
        exec:
          command: ["cat", "/tmp/healthy"]
```

## Tuning fields
```
   initialDelaySeconds  wait this long before first check
   periodSeconds        how often to check
   timeoutSeconds       per-check timeout
   successThreshold     consecutive passes to be considered healthy
   failureThreshold     consecutive fails before acting (restart/unready)
```

## Why startupProbe exists (slow apps)
```
   Without startupProbe:
     liveness fires too early -> app still booting -> killed in a loop
   With startupProbe:
     liveness/readiness are PAUSED until startup passes -> safe slow boot
```

## Timeline (ASCII)
```
   t0 ---- startupProbe passes ----+
                                   |--> readiness + liveness begin
   ready? no -> no traffic         |
   ready? yes -> added to Service endpoints
   liveness fails repeatedly -> container restarted
```

## Inspect
```bash
kubectl describe pod app        # see probe results + restart reasons
kubectl get pod app             # READY column, RESTARTS count
kubectl get endpoints <svc>     # readiness controls who is listed here
```

## Key takeaways
- **Liveness restarts; Readiness gates traffic; Startup protects slow boots.**
- A pod can be **Live but not Ready** (running, no traffic).
- Probe via **httpGet / tcpSocket / exec**; tune with delay/period/thresholds.

## Checklist
- [ ] Added readiness + liveness probes to a pod
- [ ] Forced readiness to fail and saw it drop from Service endpoints
- [ ] Forced liveness to fail and saw RESTARTS increment
- [ ] Used a startupProbe for a slow-starting app
