# Day 7 — Pods: Imperative vs Declarative & YAML

> Video: Day 7/40 — Pod In Kubernetes | Imperative VS Declarative | YAML
> https://www.youtube.com/watch?v=_f9ql2Y5Xcc
> Duration: ~33 min

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
```bash
kubectl run nginx --image=nginx              # create a pod fast
kubectl get pods
kubectl get pods -o wide                      # node + pod IP
kubectl describe pod nginx                     # events & details
kubectl delete pod nginx
```

## Declarative: a Pod YAML
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
```
   apiVersion:  which API group/version  (e.g. v1, apps/v1)
   kind:        object type              (Pod, Deployment...)
   metadata:    name, labels, namespace
   spec:        desired state of the object
```

## Pro tip: generate YAML instead of hand-writing (exam gold)
```bash
# --dry-run=client builds the YAML WITHOUT creating anything
kubectl run nginx --image=nginx \
  --dry-run=client -o yaml > pod.yaml
```

## Debugging a pod
```bash
kubectl describe pod nginx       # see Events at the bottom
kubectl logs nginx               # container stdout/stderr
kubectl exec -it nginx -- bash   # shell inside
```

## Imperative -> Declarative mental model
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
