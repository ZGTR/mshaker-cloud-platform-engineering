# Day 11 — Multi-Container Pods: Sidecar vs Init Container

> Video: Day 11/40 — Multi Container Pod Kubernetes — Sidecar vs Init Container
> https://www.youtube.com/watch?v=yRiFq1ykBxc
> Duration: ~25 min

## Recap: a pod can hold multiple containers
They share the **same network (localhost) and volumes**. Use this when helper
containers must live and die with the main app.

```
   +------------------- POD -------------------+
   |  shared IP + shared volume                 |
   |  +-----------+   +---------------------+    |
   |  | main app  |<->| sidecar (helper)    |    |
   |  +-----------+   +---------------------+    |
   |  talk via localhost; share /data volume    |
   +-------------------------------------------+
```

## Two patterns

### 1) Init Containers — run BEFORE, in order, to completion
Init containers run **one after another to completion** before the main
container ever starts.

```
   TIME ->
   [ initC-1 ] done
              [ initC-2 ] done
                         [ main container starts ]
   - Run sequentially, each must succeed.
   - Used for setup: wait for a DB, clone config, run migrations.
```

### 2) Sidecar — runs ALONGSIDE the main container, whole pod lifetime
A sidecar runs **concurrently** with the main container for the entire life of
the pod.

```
   [ main app        ============================ ]
   [ sidecar(logging)============================ ]
   - Both run together for the life of the pod.
   - Used for: log shippers, proxies, file sync, metrics agents.
```

## Init container YAML
This pod blocks on an init container until the database port is reachable, then
starts the app.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  initContainers:
    - name: wait-for-db
      image: busybox
      command: ['sh','-c','until nc -z db 5432; do sleep 2; done']
  containers:
    - name: app
      image: myapp:1.0
```

## Sidecar YAML (shared volume)
Here a log-shipper sidecar shares an **emptyDir** volume with the web container
to read its logs.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  volumes:
    - name: logs
      emptyDir: {}
  containers:
    - name: web
      image: nginx
      volumeMounts:
        - name: logs
          mountPath: /var/log/nginx
    - name: log-shipper        # sidecar reads the same logs
      image: busybox
      command: ['sh','-c','tail -f /logs/access.log']
      volumeMounts:
        - name: logs
          mountPath: /logs
```

## Init vs Sidecar
Quick side-by-side of when each pattern runs and what it's for.

| | Init Container | Sidecar |
|---|----------------|---------|
| When | before main starts | alongside main |
| Lifetime | runs then exits | lives whole pod |
| Order | sequential, must pass | concurrent |
| Use | setup/wait/migrate | logging/proxy/sync |

## Inspect
Commands to watch init progress and read logs from a specific container with
`-c`.

```bash
kubectl get pod app                       # READY shows init progress
kubectl logs app -c wait-for-db           # logs of a specific container
kubectl describe pod app                  # Init Containers section
```

## Key takeaways
- Multiple containers in a pod share **network + volumes**.
- **Init** = pre-flight, sequential, must finish first.
- **Sidecar** = co-running helper for the pod's whole life.

## Checklist
- [ ] Built a pod with an init container that gates startup
- [ ] Built a sidecar sharing an emptyDir volume with the main app
- [ ] Read logs of a specific container with `-c`
