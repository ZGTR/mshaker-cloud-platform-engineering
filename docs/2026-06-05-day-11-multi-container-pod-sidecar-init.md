# Day 11 — Multi-Container Pods: Sidecar vs Init Container

> Video: Day 11/40 — Multi Container Pod Kubernetes — Sidecar vs Init Container
> https://www.youtube.com/watch?v=yRiFq1ykBxc
> Duration: ~25 min

## Key terms
| Term | Meaning |
| --- | --- |
| Multi-container pod | A pod holding more than one container |
| Sidecar | Helper container running alongside the main app |
| Init container | Runs to completion before app containers start |
| Shared volume | Storage mounted by several containers in a pod |
| Pod network | Shared localhost/IP among a pod's containers |

## Problem & solution
Some helper concerns (log shipping, setup tasks, proxies) need to share a
lifecycle, network, and disk with the main app. Running them as separate pods
loses that tight coupling, so we sometimes pack multiple containers into one pod.

**Solution:** Co-locate helper containers in one pod, init containers run first and sidecars run alongside, sharing the pod's network and volumes.

## Where this fits in the cluster
Today's topic lives at the **container** layer — multiple containers packed
inside a single pod. Here is the full stack so you can see where that is.

```
   +------------------------------- CLUSTER --------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | +----------------------------------------------------------------+     |
   | +---------- WORKER NODE   (kubelet | kube-proxy | runtime) ----------+ |
   | | +---------------------- namespace: default ----------------------+ | |
   | | | +--------------------------- POD ----------------------------+ | | |
   | | | | +---------------------- CONTAINER -----------------------+ | | | |
   | | | | | app                                                    | | | | |
   | | | | |    <== init runs first; sidecar runs alongside the app | | | | |
   | | | | +--------------------------------------------------------+ | | | |
   | | | +------------------------------------------------------------+ | | |
   | | +----------------------------------------------------------------+ | |
   | +--------------------------------------------------------------------+ |
   +------------------------------------------------------------------------+
```

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

### What is (and isn't) shared
A pod is a **shared fate + shared namespace** boundary. Some Linux namespaces
are shared by default, others are not.

```
   SHARED across all containers in the pod        NOT shared (per-container)
   ------------------------------------------     ---------------------------
   * Network namespace (one IP, one port space)   * Filesystem / root (/)
       -> reach each other on 127.0.0.1           * Process list (unless
   * IPC namespace (shared memory, semaphores)        shareProcessNamespace)
   * Mounted Volumes you explicitly mount         * Container image + binaries
   * UTS (hostname)                                * cgroup limits (per cntr)
```

> Mental model: containers in a pod are like **processes on one machine** that
> can talk over `localhost` and share scratch disks, but each ships its own
> root filesystem and tools.

### Port collisions are real
Because the pod has **one network namespace**, two containers cannot both bind
the same port. Plan ports up front.

```
   POD (10.1.2.3)
   +--------------------------+--------------------------+
   | web      :8080  OK       | proxy   :8080  CONFLICT! |
   | metrics  :9090  OK       |  -> only one :8080 wins   |
   +--------------------------+--------------------------+
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

If any init container **fails**, the kubelet restarts the pod (per
`restartPolicy`) and re-runs init from the top — the app containers never see a
half-finished setup.

```
   initC-1 OK -> initC-2 FAIL  ==>  back off, restart pod, run initC-1 again
                    ^                      |
                    +----- retry loop -----+
   App container stays PENDING until ALL init containers succeed.
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

### Side-by-side on one timeline
Putting both on a single clock makes the difference obvious: init is a
**prologue**, the sidecar is a **companion**.

```
   t0        t1            t2 ........................... tN (pod deleted)
   |---------|-------------|-------------------------------|
   [initC]   done
             [ main app    =============================== ]
             [ sidecar     =============================== ]
    setup     |  both main + sidecar run together until    |
    phase     |  the pod is terminated                     |
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

### How the shared volume wires up
`emptyDir` is a scratch disk created with the pod and deleted with it. Both
containers mount the **same** volume — at different paths — so one writes and
the other reads.

```
                 emptyDir volume "logs"  (lives + dies with the pod)
                 +----------------------------+
                 |   access.log   error.log   |
                 +----------------------------+
                   ^  mount: /var/log/nginx       (web WRITES here)
                   |
        +----------+-----------+        +------------------------+
        |  web (nginx)         |        |  log-shipper (busybox) |
        |  writes access.log   |        |  tail -f /logs/...     |
        +----------------------+        +------------------------+
                                          ^  mount: /logs  (READS here)
```

### Native sidecars (Kubernetes 1.29+)
Classic sidecars are just extra entries under `containers:` — but they have a
flaw: at pod shutdown there's **no ordering**, and during startup the app may
boot before the sidecar (proxy/auth) is ready. Modern Kubernetes models a
sidecar as an **init container with `restartPolicy: Always`**, which gives it a
proper lifecycle: starts before the app, stays running, and is torn down last.

```
   Classic sidecar (containers[]):    Native sidecar (initContainers[]):
     start order: undefined             starts BEFORE app, app waits for it
     shutdown:    undefined             shuts down AFTER app (clean drain)
     keeps pod from "Completing"        Job pods can now Complete cleanly
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-native-sidecar
spec:
  initContainers:
    - name: log-shipper
      image: busybox
      restartPolicy: Always          # <-- this makes it a native sidecar
      command: ['sh','-c','tail -F /logs/access.log']
      volumeMounts:
        - { name: logs, mountPath: /logs }
  containers:
    - name: web
      image: nginx
      volumeMounts:
        - { name: logs, mountPath: /var/log/nginx }
  volumes:
    - name: logs
      emptyDir: {}
```

## Init vs Sidecar
Quick side-by-side of when each pattern runs and what it's for.

| | Init Container | Sidecar (classic) | Native Sidecar (1.29+) |
|---|----------------|---------|---------|
| Declared under | `initContainers` | `containers` | `initContainers` + `restartPolicy: Always` |
| When | before main starts | alongside main | starts before main, runs alongside |
| Lifetime | runs then exits | lives whole pod | lives whole pod, stops after main |
| Order | sequential, must pass | concurrent, undefined | ordered start + ordered drain |
| Use | setup/wait/migrate | logging/proxy/sync | logging/proxy in Jobs + clean drain |

## Sidecar use cases in the wild
Sidecars keep the main image **single-purpose** by offloading cross-cutting
concerns into a neighbor container.

```
   Log shipper    : tail app logs -> ship to Loki/ELK   (no log code in app)
   Service mesh    : Envoy proxy intercepts all traffic  (mTLS, retries)
   Config reloader : watch a ConfigMap -> signal app     (hot reload)
   File sync       : git-sync clones a repo into a volume (static content)
   Metrics adapter : translate app stats -> Prometheus    (exporter)
```

## Common pitfalls
The failure modes that bite people first.

```
   * Init never finishes  -> pod stuck Init:0/1; check `kubectl logs -c <init>`
   * Wrong mountPath       -> sidecar reads an empty dir; paths must match the
                             SAME volume name, not the same path
   * Port collision        -> two containers binding one port; pod won't be Ready
   * Classic sidecar in a  -> Job never reaches Complete because the sidecar
     Job                      keeps running; use a NATIVE sidecar instead
   * Sidecar OOM/crashloop -> can take the whole pod's Ready status down
```

## Inspect
Commands to watch init progress and read logs from a specific container with
`-c`.

```bash
kubectl get pod app                       # READY shows init progress
kubectl logs app -c wait-for-db           # logs of a specific container
kubectl logs app -c log-shipper -f        # follow a sidecar's logs live
kubectl describe pod app                  # Init Containers section
kubectl exec -it app -c web -- sh         # shell INTO a specific container
```

### Reading the STATUS column
`kubectl get pod` encodes init progress right in the status — learn to read it
at a glance.

```
   NAME   READY   STATUS            meaning
   app    0/1     Init:0/2          waiting on init container 1 of 2
   app    0/1     Init:1/2          init 1 done, init 2 running
   app    0/1     Init:Error        an init container exited non-zero
   app    0/1     Init:CrashLoop... init keeps failing, backing off
   app    0/1     PodInitializing   init done, main containers starting
   app    1/1     Running           all good
```

## Decision guide
A quick flow for picking the right multi-container pattern.

```
   Does the helper need to FINISH before the app starts?
        |
        +-- yes --> Init Container (wait/migrate/seed)
        |
        +-- no, it runs the whole time alongside the app
                |
                +-- pod is a Job, or you need ordered start/drain?
                        |
                        +-- yes --> Native Sidecar (initContainers + Always)
                        |
                        +-- no  --> Classic Sidecar (extra containers[] entry)

   Helper belongs on EVERY node, not per-app?  -> DaemonSet (Day 12), not a sidecar
```

## End-to-end example: init + sidecar together
A web pod that (1) waits for its config to be cloned by an **init container**,
then (2) serves traffic while a **sidecar** ships its logs. One pod, three
containers, one shared volume.

```
   t0  [init: git-clone config] -> done
   t1  [ web (nginx)      ============================ ]
       [ log-shipper      ============================ ]   <- sidecar
            both share emptyDir "content" + "logs"
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-e2e
  labels: { app: web }
spec:
  volumes:
    - name: content
      emptyDir: {}
    - name: logs
      emptyDir: {}
  initContainers:
    - name: clone-config                 # 1) PRE-FLIGHT, must finish first
      image: alpine/git
      command: ['sh','-c','git clone https://example.com/site /content || mkdir -p /content']
      volumeMounts:
        - { name: content, mountPath: /content }
  containers:
    - name: web                          # 2) main app
      image: nginx
      ports: [{ containerPort: 80 }]
      volumeMounts:
        - { name: content, mountPath: /usr/share/nginx/html }
        - { name: logs, mountPath: /var/log/nginx }
    - name: log-shipper                  # 3) sidecar, runs alongside web
      image: busybox
      command: ['sh','-c','tail -F /logs/access.log']
      volumeMounts:
        - { name: logs, mountPath: /logs }
```

```bash
kubectl apply -f web-e2e.yaml
kubectl get pod web-e2e -w                 # Init:0/1 -> PodInitializing -> Running
kubectl logs web-e2e -c clone-config        # see the init step
kubectl logs web-e2e -c log-shipper -f      # follow the sidecar tail
kubectl exec -it web-e2e -c web -- curl localhost   # main app serves content
```

## Key takeaways
- Multiple containers in a pod share **network (localhost) + IPC + mounted
  volumes**, but each keeps its own filesystem and tools.
- **Init** = pre-flight, sequential, must finish first; failure restarts the pod.
- **Sidecar** = co-running helper for the pod's whole life.
- **Native sidecar** (`initContainers` + `restartPolicy: Always`) gives ordered
  startup and clean drain — essential for Jobs and proxies.
- Use `-c <container>` to target logs/exec at one container in a multi-container
  pod.

## Checklist
- [ ] Built a pod with an init container that gates startup
- [ ] Watched the STATUS column move `Init:0/1 -> PodInitializing -> Running`
- [ ] Built a sidecar sharing an emptyDir volume with the main app
- [ ] Converted it to a native sidecar with `restartPolicy: Always`
- [ ] Read logs of a specific container with `-c`
- [ ] Shelled into a specific container with `kubectl exec -c`
