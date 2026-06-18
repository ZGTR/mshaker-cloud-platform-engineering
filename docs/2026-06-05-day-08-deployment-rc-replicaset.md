# Day 8 — Deployment, Replication Controller & ReplicaSet

> Video: Day 8/40 — Kubernetes Deployment, Replication Controller and ReplicaSet
> https://www.youtube.com/watch?v=oe2zjRb51F0
> Duration: ~35 min

## Key terms
| Term | Meaning |
| --- | --- |
| Deployment | Manages ReplicaSets for rolling updates and rollback |
| ReplicaSet (RS) | Keeps N pod replicas running |
| ReplicationController (RC) | Legacy predecessor of the ReplicaSet |
| Replica | One copy of a pod |
| Rolling update | Gradual pod replacement with no downtime |
| Rollback | Revert to a previous revision |
| Selector | Label query matching the managed pods |

## Problem & solution
A bare pod has no self-healing and no scaling: if it dies, it's gone, and there
is no safe way to roll out a new version. We need controllers that keep a
desired number of pod copies alive and manage rollouts.

**Solution:** Use a Deployment to manage a ReplicaSet that keeps N pod replicas running and enables rolling updates and rollbacks.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------ CLUSTER ------------------------------+
   | +------------------------- CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+  | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr |  | |
   | | +------------+   +------+   +-----------+   +----------------+  | |
   | | controller-mgr  <== Deployment -> ReplicaSet keeps N pods alive | |
   | +-----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                  |
   | | +---------- namespace: default ----------+     |                  |
   | | | +--------------- POD ----------------+ |     |                  |
   | | | | + CONTAINER +                      | |     |                  |
   | | | | | app       |                      | |     |                  |
   | | | | +-----------+                      | |     |                  |
   | | | |    <== one of N identical replicas | |     |                  |
   | | | +------------------------------------+ |     |                  |
   | | +----------------------------------------+     |                  |
   | +------------------------------------------------+                  |
   +---------------------------------------------------------------------+
```

## Why not just run bare Pods?
A lone pod has **no self-healing and no scaling**. If it dies, it's gone.
Controllers keep a desired number of pod copies alive.

## The hierarchy (ASCII)
Controllers stack on top of each other — a Deployment owns ReplicaSets, which
own the Pods.

```
   Deployment           (rollouts, rollbacks, versioning)
      |
      v
   ReplicaSet           (keeps N identical pods running)
      |
      +----+----+----+
      v    v    v    v
    Pod   Pod  Pod  Pod   (the actual workload)
```

- **Replication Controller (RC)**: the OLD way to keep N pods (legacy).
- **ReplicaSet (RS)**: the newer RC, supports set-based label selectors.
- **Deployment**: manages ReplicaSets; adds rolling updates & rollbacks.
  -> **Use Deployments in practice.**

## Self-healing & scaling
The ReplicaSet constantly compares **actual** vs **desired** pod count and
recreates any that die.

```
   desired replicas = 3
   +-----+ +-----+ +-----+
   | pod | | pod | | pod |
   +-----+ +--x--+ +-----+      <- one pod dies
              |
              v   ReplicaSet notices actual(2) != desired(3)
   +-----+ +-----+ +-----+
   | pod | | NEW | | pod |      <- recreates automatically
   +-----+ +-----+ +-----+
```

## Deployment YAML
A Deployment manifest wraps a Pod **template** plus a replica count and a label
**selector**.

`deploy.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web            # MUST match template labels
  template:               # this is the Pod spec
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
```

```bash
kubectl apply -f deploy.yaml
kubectl get deploy,rs,pods           # see all three layers
kubectl get pods -l app=web          # filter by label
```

## Scaling
Change the replica count to scale up or down — imperatively or by editing the
YAML.

```bash
kubectl scale deployment web --replicas=5     # imperative
# or edit replicas in YAML and re-apply (declarative)
```

## Rolling updates & rollback (the Deployment superpower)
Deployments swap pods gradually between old and new ReplicaSets, giving
**zero-downtime** updates you can undo.

```
   Old RS (v1)            New RS (v2)
   [p][p][p]   ---->      [ ][ ][ ]
   gradually scale down old, scale up new = zero downtime
```

```bash
kubectl set image deployment/web nginx=nginx:1.28   # trigger update
kubectl rollout status deployment/web               # watch progress
kubectl rollout history deployment/web              # revisions
kubectl rollout undo deployment/web                 # rollback!
```

## RS vs RC selector difference
The key upgrade from ReplicationController to ReplicaSet is **set-based** label
selectors.

```
  ReplicationController: equality only   ->  app = web
  ReplicaSet: set-based too              ->  app in (web, api)
```

## Key takeaways
- Hierarchy: **Deployment -> ReplicaSet -> Pods**.
- `selector.matchLabels` MUST match `template.metadata.labels`.
- Deployments add **rolling updates + rollback**; prefer them over RS/RC.

## Checklist
- [ ] Created a Deployment with 3 replicas
- [ ] Killed a pod, watched it self-heal
- [ ] Scaled up/down
- [ ] Did a rolling update and an `undo` rollback
