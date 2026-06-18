# Day 7 — Pods: Imperative vs Declarative & YAML

> Video: Day 7/40 — Pod In Kubernetes | Imperative VS Declarative | YAML
> https://www.youtube.com/watch?v=_f9ql2Y5Xcc
> Duration: ~33 min

## Key terms
| Term | Meaning |
| --- | --- |
| Pod | Smallest deployable unit (one or more containers) |
| Imperative | Do-this-now commands (`kubectl run`/`create`) |
| Declarative | Apply desired YAML and let Kubernetes converge |
| Manifest | A YAML/JSON object definition |
| apiVersion/kind/metadata/spec | The four required top-level YAML fields |
| `--dry-run=client` | Build YAML without creating anything |
| `kubectl apply` | Declarative create/update from a manifest |

## Problem & solution
The pod is the unit you actually deploy, but there are two very different ways
to create resources: quick imperative commands versus versionable declarative
YAML. Choosing wrong leads to unrepeatable, undocumented infrastructure.

**Solution:** Define workloads declaratively in YAML and apply them, so the cluster reconciles to your desired state (prefer declarative over imperative one-offs).

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | +----------------------------------------------------------------+ |
   | +------- WORKER NODE   (kubelet | kube-proxy | runtime) --------+  |
   | | +------------------- namespace: default --------------------+ |  |
   | | | +------------------------- POD -------------------------+ | |  |
   | | | | +-------------------- CONTAINER --------------------+ | | |  |
   | | | | | app                                               | | | |  |
   | | | | |    <== shares network + storage with pod siblings | | | |  |
   | | | | +---------------------------------------------------+ | | |  |
   | | | |    <== smallest deployable unit                       | | |  |
   | | | +-------------------------------------------------------+ | |  |
   | | +-----------------------------------------------------------+ |  |
   | +---------------------------------------------------------------+  |
   +--------------------------------------------------------------------+
```

## What is a Pod?
The **smallest deployable unit** in Kubernetes. A pod wraps one (or more)
containers that **share network (same IP) and storage**.

```
   +------------------ POD ------------------+
   |  shared IP  +  shared volumes            |
   |   +-------------+   +-------------+       |
   |   | container A |   | container B |       |
   |   +-------------+   +-------------+       |
   |        localhost between them            |
   +------------------------------------------+
   - You usually run ONE main container per pod.
   - Pods are ephemeral: they get replaced, not repaired.
```

## Two ways to manage objects
Kubernetes accepts both styles: you can fire off **imperative** commands or hand
it a **declarative** file describing the end state.

```
   IMPERATIVE  = tell K8s the exact COMMANDS to run (how)
   DECLARATIVE = give K8s a YAML of the desired STATE (what)
```

| | Imperative | Declarative |
|---|------------|-------------|
| Style | `kubectl run/create ...` | `kubectl apply -f file.yaml` |
| Best for | quick tests, exam speed | real/version-controlled infra |
| Repeatable | hard to track | yes (GitOps-friendly) |
| Idempotent | no | yes (re-apply = no-op) |

## Imperative examples
Quick one-off commands that create and inspect a pod without writing any YAML.

```bash
kubectl run nginx --image=nginx              # create a pod fast
kubectl get pods
kubectl get pods -o wide                      # node + pod IP
kubectl describe pod nginx                     # events & details
kubectl delete pod nginx
```

## Declarative: a Pod YAML
Here the desired state lives in a file you version-control and `apply` — the
preferred way for real infrastructure.

`pod.yaml`:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
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
kubectl apply -f pod.yaml      # create or update to match file
kubectl get pod nginx -o yaml  # full live spec
kubectl delete -f pod.yaml
```

## The 4 required top-level YAML fields
Every Kubernetes manifest needs these four keys at the top.

```
   apiVersion:  which API group/version  (e.g. v1, apps/v1)
   kind:        object type              (Pod, Deployment...)
   metadata:    name, labels, namespace
   spec:        desired state of the object
```

## Pro tip: generate YAML instead of hand-writing (exam gold)
Let kubectl write the boilerplate for you, then tweak the file instead of typing
YAML from scratch.

```bash
# --dry-run=client builds the YAML WITHOUT creating anything
kubectl run nginx --image=nginx \
  --dry-run=client -o yaml > pod.yaml
```

## Debugging a pod
When a pod misbehaves, these three commands surface events, logs, and a shell
inside the container.

```bash
kubectl describe pod nginx       # see Events at the bottom
kubectl logs nginx               # container stdout/stderr
kubectl exec -it nginx -- bash   # shell inside
```

## Imperative -> Declarative mental model
A handy workflow: generate a manifest from an imperative command, then manage it
declaratively from then on.

```
   kubectl run nginx --image=nginx
        |  (generate)
        v
   pod.yaml  --kubectl apply-->  cluster state in etcd
```

## Key takeaways
- Pod = smallest unit; containers in it share IP + storage.
- Use **imperative** for speed, **declarative** for real infra.
- `--dry-run=client -o yaml` generates manifests fast (use it in the exam).

## Checklist
- [ ] Created a pod imperatively and declaratively
- [ ] Generated YAML with `--dry-run=client -o yaml`
- [ ] Used `describe`, `logs`, `exec` to inspect a pod
