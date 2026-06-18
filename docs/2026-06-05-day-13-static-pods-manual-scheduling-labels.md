# Day 13 — Static Pods, Manual Scheduling, Labels & Selectors

> Video: Day 13/40 — Static Pods, Manual Scheduling, Labels, and Selectors
> https://www.youtube.com/watch?v=6eGf7_VSbrQ
> Duration: ~30 min

## Problem & solution
Sometimes you must run a pod without the scheduler or even the API server (like
control-plane bootstrap), pin a pod to a specific node, and reliably group and
find objects. Static pods, `nodeName`, and labels/selectors solve these.

**Solution:** Place pod manifests in the kubelet's manifest directory for node-managed static pods, and use labels/nodeName for manual scheduling.

## Where this fits in the cluster
Today touches three layers: **static pods** are created by the kubelet on a
node, **manual scheduling** bypasses the scheduler, and **labels/selectors** are
the glue used everywhere.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | scheduler  <== bypassed by static pods + nodeName              | |
   | +----------------------------------------------------------------+ |
   | +------- WORKER NODE   (kubelet | kube-proxy | runtime) -------+   |
   | |    <== kubelet reads /etc/kubernetes/manifests -> static pod |   |
   | | + namespace: default +                                       |   |
   | | | +----- POD -----+  |                                       |   |
   | | | | + CONTAINER + |  |                                       |   |
   | | | | | app       | |  |                                       |   |
   | | | | +-----------+ |  |                                       |   |
   | | | +---------------+  |                                       |   |
   | | +--------------------+                                       |   |
   | +--------------------------------------------------------------+   |
   +--------------------------------------------------------------------+
```

## What the kubelet is (the node agent)
The **kubelet** is the agent that runs on **every node**. It's the bridge
between the control plane's *desired state* and the *real containers* running on
that machine. The api-server decides "this pod should run on node-2"; the
kubelet on node-2 actually makes it happen and keeps reporting back.

```
   CONTROL PLANE
     api-server  <----------- registers node + reports pod/node status -------+
        |   ^                  (Running / Ready / RESTARTS, live usage)        |
        |   | watch: "you own these PodSpecs"                                  |
        v   |                                                                  |
   +------------------------------- NODE ----------------------------------+   |
   |  kubelet  (node agent)                                                |---+
   |    | 1. read PodSpec (from api-server) OR static file (from disk)     |
   |    v                                                                  |
   |  CRI  (containerd / CRI-O)  -- pull image, create + start container   |
   |    |                                                                  |
   |    v                                                                  |
   |  [ container ]   [ container ]                                        |
   |                                                                       |
   |  also does:  run probes (Day 18) · mount volumes · inject             |
   |              ConfigMaps/Secrets (Day 19) · enforce limits via         |
   |              cgroups (Day 16) · restart crashed containers            |
   +-----------------------------------------------------------------------+
```

What the kubelet does **not** do: it does not *pick* the node (that's the
scheduler) and it does not run cluster-wide logic (that's the controllers). It
only manages the pods assigned to its own node.

```
   scheduler  -> DECIDES which node           (placement)
   kubelet    -> RUNS + watches pods on ITS node  (execution)   <== Day 13
   runtime    -> actually creates the container    (containerd/CRI-O)
```

> One-liner: **the kubelet is the per-node worker that turns PodSpecs into
> running containers and reports their health back to the api-server.**
> Static pods are special because the kubelet reads them straight from disk —
> no api-server or scheduler needed.

## Static Pods — managed by kubelet, not the API server
A **static pod** is created directly by the kubelet from a local file, bypassing
the scheduler and API server entirely.

```
   Normal pod:   apiserver -> scheduler -> kubelet -> pod
   Static pod:   kubelet reads a FILE on disk -> pod
                 (no scheduler, no apiserver needed to create)
```
The kubelet watches a directory (default
`/etc/kubernetes/manifests/`). Drop a pod YAML there -> kubelet runs it and
keeps it alive. This is how **control-plane components** (apiserver, etcd,
controller-manager, scheduler) themselves run.

```
   /etc/kubernetes/manifests/
        kube-apiserver.yaml      -> static pod
        etcd.yaml                -> static pod
        my-static.yaml           -> your static pod
```

- A read-only **mirror pod** appears in the API for visibility, but you can't
  delete it via `kubectl` — you must remove the file.

```bash
# find the manifest path
grep staticPodPath /var/lib/kubelet/config.yaml
# static pods show with the node name as a suffix
kubectl get pods -A -o wide | grep <node-name>
```

## Manual Scheduling — bypass the scheduler with nodeName
Setting **`spec.nodeName`** hardcodes which node a pod runs on, skipping the
scheduler's normal placement decision.

```
   Normal:  scheduler picks node based on resources/affinity
   Manual:  you hardcode spec.nodeName -> pod lands there directly
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
spec:
  nodeName: cka-worker2      # skip scheduler, go to this node
  containers:
    - name: nginx
      image: nginx
```
Used when the scheduler is down or for special placement. If `nodeName` is set,
the scheduler is skipped entirely.

## Labels & Selectors — the glue of Kubernetes
**Labels** are key/value tags you attach to objects, and **selectors** are
queries that find objects by those labels — this is how Kubernetes wires
resources together.

```
   Labels   = key/value tags ON objects        app=web, env=prod
   Selector = a query to FIND objects by labels app=web

   [pod app=web env=prod]  [pod app=web env=dev]  [pod app=api]
            \_____________ selector app=web _______/
                      matches first two
```

```bash
kubectl label pod nginx tier=frontend       # add a label
kubectl get pods --show-labels
kubectl get pods -l app=web                  # equality selector
kubectl get pods -l 'env in (dev,prod)'      # set-based selector
kubectl get pods -l app=web,env=prod         # AND of two labels
kubectl label pod nginx tier-                # remove label (trailing -)
```

## Where selectors are used
Selectors show up across many resource types, each using labels to decide which
pods or nodes they target.

```
   Service        -> selects which pods to route to
   Deployment/RS  -> selects which pods it owns
   NetworkPolicy  -> selects which pods a rule applies to
   nodeSelector   -> pod picks nodes by node labels
```

## nodeSelector (simple node targeting)
**`nodeSelector`** is the simplest way to constrain a pod to nodes carrying a
specific label.

```yaml
spec:
  nodeSelector:
    disktype: ssd      # only schedule on nodes labeled disktype=ssd
```
```bash
kubectl label node cka-worker disktype=ssd
```

## End-to-end example: label, pin, and select
Run two labeled pods (one pinned to a specific node), then use a Service that
selects them by label — showing how labels wire pods to a Service.

```
   [pod web-a app=web,env=prod]  on node-1
   [pod web-b app=web,env=prod]  on node-2 (pinned via nodeName)
            \________ Service selector app=web ________/
                        routes to BOTH pods
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-b
  labels: { app: web, env: prod }
spec:
  nodeName: cka-worker2         # manual scheduling: skip the scheduler
  containers:
    - name: nginx
      image: nginx
---
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  selector: { app: web }        # selector matches the pod labels above
  ports:
    - port: 80
      targetPort: 80
```

```bash
kubectl run web-a --image=nginx --labels="app=web,env=prod"
kubectl apply -f web-b-and-svc.yaml
kubectl get pods -o wide -l app=web         # see both, and which nodes
kubectl get endpoints web                   # both pod IPs listed via the selector
kubectl get pods -l 'env in (prod)'         # set-based selector query
```

## Key takeaways
- **Static pods** are file-managed by kubelet; that's how the control plane runs.
- **`nodeName`** pins a pod to a node, skipping the scheduler.
- **Labels + selectors** connect Services, controllers, policies to pods.

## Checklist
- [ ] Created a static pod via the manifests directory
- [ ] Pinned a pod to a node with `nodeName`
- [ ] Added/removed labels and queried with `-l` (equality + set-based)
- [ ] Used `nodeSelector` with a node label
