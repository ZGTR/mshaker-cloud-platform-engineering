# Day 14 — Taints and Tolerations

> Video: Day 14/40 — Taints and Tolerations in Kubernetes
> https://www.youtube.com/watch?v=nwoS2tK2s6Q
> Duration: ~26 min

## Problem & solution
By default the scheduler can place any pod on any node, but some nodes are
special (GPU, dedicated, control-plane) and should repel general workloads
unless a pod explicitly opts in.

**Solution:** Taint nodes to repel pods, and add matching tolerations to the pods allowed to run there, to dedicate nodes.

## Where this fits in the cluster
Taints live on **nodes**; tolerations live on **pods**. The **scheduler** reads
both to decide placement. This is a node-level admission gate.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | scheduler  <== checks node taints vs pod tolerations           | |
   | +----------------------------------------------------------------+ |
   | +-- WORKER NODE   (kubelet | kube-proxy | runtime) --+             |
   | |    <== a taint repels pods unless they tolerate it |             |
   | | + namespace: default +                             |             |
   | | | +----- POD -----+  |                             |             |
   | | | | + CONTAINER + |  |                             |             |
   | | | | | app       | |  |                             |             |
   | | | | +-----------+ |  |                             |             |
   | | | +---------------+  |                             |             |
   | | +--------------------+                             |             |
   | +----------------------------------------------------+             |
   +--------------------------------------------------------------------+
```

## The idea
**Taints repel pods from nodes. Tolerations let specific pods stick anyway.**
It's the opposite of attraction — taints push pods AWAY unless they tolerate it.

```
   Node with taint gpu=true:NoSchedule
   +-------------------------------+
   |   "Keep out, unless you have  |
   |    a matching toleration."     |
   +-------------------------------+
        ^                    ^
        | NO toleration      | HAS toleration
     [pod A] x blocked     [pod B] allowed in
```

> Mnemonic: **Taint = the bouncer on the node. Toleration = the VIP pass on the pod.**
> Note: a toleration *allows* placement; it does not *force* it (that's affinity).

## Taint a node
You apply a **taint** to a node with `kubectl taint`, and remove it by repeating
the command with a trailing minus.

```bash
kubectl taint nodes cka-worker gpu=true:NoSchedule
kubectl describe node cka-worker | grep -i taint

# remove a taint (trailing minus)
kubectl taint nodes cka-worker gpu=true:NoSchedule-
```

Taint format:
```
   key = value : effect
   gpu = true  : NoSchedule
```

## The 3 taint effects
The **effect** decides how harshly the taint treats pods that don't tolerate it,
ranging from soft avoidance to outright eviction.

```
   NoSchedule        -> new pods without toleration are NOT placed here
   PreferNoSchedule  -> soft; avoid if possible, but allowed if needed
   NoExecute         -> also EVICTS already-running pods that don't tolerate
```

## Toleration on a pod
A **toleration** in the pod spec must match the node's taint key, value, and
effect for the pod to be allowed onto that node.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  tolerations:
    - key: "gpu"
      operator: "Equal"
      value: "true"
      effect: "NoSchedule"
  containers:
    - name: app
      image: nginx
```

`operator`:
```
   Equal   -> key, value, and effect must all match
   Exists  -> key + effect match; value ignored (tolerate any value)
```

## NoExecute extra field: tolerationSeconds
For **NoExecute** taints, `tolerationSeconds` lets a tolerating pod linger for a
set time before it is finally evicted.

```yaml
    - key: "node.kubernetes.io/not-ready"
      operator: "Exists"
      effect: "NoExecute"
      tolerationSeconds: 300     # stay 5 min after taint, then evict
```

## Why control-plane nodes run no normal pods
Control-plane nodes carry a built-in taint that keeps ordinary workloads off the
master unless they explicitly tolerate it.

```
   kubectl describe node <control-plane> | grep Taints
   -> node-role.kubernetes.io/control-plane:NoSchedule
   This taint keeps your workloads off the master by default.
```

## Taints/Tolerations vs Affinity (don't confuse them)
These solve opposite problems: taints **repel** pods from a node, while affinity
**attracts** a pod toward nodes.

```
   Taint/Toleration -> NODE repels pods   (pod needs permission to land)
   Node Affinity    -> POD attracts nodes (pod prefers/requires nodes)  [Day 15]
   Best practice: combine both to truly dedicate nodes.
```

## End-to-end example: dedicate a GPU node
Taint a node so only GPU workloads land there, then deploy a pod that tolerates
it. A plain pod is rejected; the tolerating pod is admitted.

```
   node cka-gpu  taint gpu=true:NoSchedule
   +-----------------------------+
   | x  plain-pod (no toleration) -> stays Pending elsewhere
   | OK gpu-pod  (toleration)     -> scheduled here
   +-----------------------------+
```

```bash
# 1) taint the node
kubectl taint nodes cka-gpu gpu=true:NoSchedule

# 2) a plain pod will NOT land on cka-gpu
kubectl run plain --image=nginx

# 3) a tolerating pod is allowed
kubectl apply -f gpu-pod.yaml
kubectl get pods -o wide                 # gpu-pod on cka-gpu, plain elsewhere
kubectl describe node cka-gpu | grep -i taint
```

```yaml
# gpu-pod.yaml
apiVersion: v1
kind: Pod
metadata: { name: gpu-pod }
spec:
  tolerations:
    - { key: "gpu", operator: "Equal", value: "true", effect: "NoSchedule" }
  containers:
    - name: app
      image: nginx
```

> To make the node *exclusively* GPU (force the pod onto it, not just allow it),
> add node affinity too — see Day 15's "dedicated node" pattern.

## Key takeaways
- Taint a node to repel pods; add a matching toleration to a pod to allow it.
- Effects: **NoSchedule**, **PreferNoSchedule** (soft), **NoExecute** (evicts).
- Toleration only **permits**, it does not **attract** — pair with affinity.

## Checklist
- [ ] Tainted a node and saw a pod fail to schedule
- [ ] Added a matching toleration and saw it schedule
- [ ] Tested NoExecute evicting a running pod
- [ ] Inspected the control-plane node's default taint
