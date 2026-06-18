# Day 15 — Node Affinity

> Video: Day 15/40 — Kubernetes Node Affinity Explained
> https://www.youtube.com/watch?v=5vimzBRnoDk
> Duration: ~27 min

## Key terms
| Term | Meaning |
| --- | --- |
| Node affinity | Attract pods to nodes by label rules |
| required...DuringScheduling | Hard rule — the pod must match |
| preferred...DuringScheduling | Soft rule — best effort |
| weight | Priority given to a preferred rule |
| Operator | Match logic: In/NotIn/Exists/etc. |
| nodeSelector | Simpler label-only node targeting |

## Problem & solution
`nodeSelector` only does exact-match and can't express "prefer" versus
"require". You need richer rules for steering pods toward the right nodes
without over-constraining them.

**Solution:** Use node affinity rules to attract pods to nodes with matching labels (e.g. disktype=ssd), as required or preferred.

## Where this fits in the cluster
Node affinity is a **pod** rule the **scheduler** evaluates against **node
labels**. It pulls a pod toward matching nodes (the opposite of Day 14's taints).

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | scheduler  <== matches pod affinity against node labels        | |
   | +----------------------------------------------------------------+ |
   | +----- WORKER NODE   (kubelet | kube-proxy | runtime) -----+       |
   | |    <== labeled (e.g. disktype=ssd) so pods can target it |       |
   | | + namespace: default +                                   |       |
   | | | +----- POD -----+  |                                   |       |
   | | | | + CONTAINER + |  |                                   |       |
   | | | | | app       | |  |                                   |       |
   | | | | +-----------+ |  |                                   |       |
   | | | +---------------+  |                                   |       |
   | | +--------------------+                                   |       |
   | +----------------------------------------------------------+       |
   +--------------------------------------------------------------------+
```

## What is Node Affinity?
A richer, more expressive way for a **pod to choose which nodes** it can run on,
based on **node labels**. It's the upgrade to the simple `nodeSelector`.

```
   nodeSelector  -> exact match only (disktype=ssd)
   nodeAffinity  -> operators (In, NotIn, Exists...), AND required vs preferred
```

## Attract vs repel (vs Day 14)
Keep the mental model straight: taints push pods away, whereas node affinity
pulls a pod toward the nodes it prefers.

```
   Taint/Toleration -> NODE repels pods (permission to land)
   Node Affinity    -> POD is drawn to matching nodes (preference/requirement)
```

## The two flavors
Node affinity comes in a **hard** form (must match or stay Pending) and a
**soft** form (prefer a match, but run anywhere if none exists).

```
   requiredDuringSchedulingIgnoredDuringExecution
     = HARD rule. No matching node -> pod stays Pending.

   preferredDuringSchedulingIgnoredDuringExecution
     = SOFT rule. Try to match; if none, schedule anywhere.

   "IgnoredDuringExecution" = once running, label changes won't evict the pod.
```

```
                match node?         no match?
   required:    schedule there      Pending (never runs)
   preferred:   prefer there        runs elsewhere anyway
```

## Required (hard) example
A **required** rule is a hard constraint — if no node matches the expression, the
pod never schedules.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ssd-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: disktype
                operator: In
                values: ["ssd"]
  containers:
    - name: app
      image: nginx
```

## Preferred (soft) example with weight
A **preferred** rule is best-effort; each preference carries a `weight` so the
scheduler can rank competing soft rules.

```yaml
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 1                 # 1-100; higher = stronger preference
          preference:
            matchExpressions:
              - key: zone
                operator: In
                values: ["us-east-1a"]
```

## Operators
Match expressions support several **operators** for comparing a node label
against your criteria.

```
   In        label value is in the list
   NotIn     label value is NOT in the list  (anti-affinity-ish)
   Exists    label key exists (any value)
   DoesNotExist  label key absent
   Gt / Lt   greater/less than (numeric)
```

## Setup: label your nodes
Affinity matches on node labels, so first tag the nodes you want to target.

```bash
kubectl label node cka-worker disktype=ssd
kubectl get nodes --show-labels
kubectl get nodes -l disktype=ssd
```

## Verify scheduling
After applying the pod, confirm where it landed and inspect events to explain any
Pending state.

```bash
kubectl apply -f ssd-pod.yaml
kubectl get pod ssd-pod -o wide        # which node did it land on?
kubectl describe pod ssd-pod           # events explain Pending if no match
```

## nodeSelector vs nodeAffinity
Side by side, `nodeAffinity` is the more expressive successor to the simple
`nodeSelector` map.

| | nodeSelector | nodeAffinity |
|---|--------------|--------------|
| Syntax | simple map | expressions + operators |
| Hard/soft | hard only | required (hard) + preferred (soft) |
| Power | exact match | In/NotIn/Exists/Gt/Lt |

## Best practice: combine with taints
To truly dedicate a node, pair taints/tolerations with node affinity so only your
pod can land there and it is forced to do so.

```
   Taint node (repel everyone) + Toleration (let my pod in) +
   Node Affinity (force my pod TO that node) = truly dedicated node.
```

## End-to-end example: pin to SSD, prefer a zone
A pod that **must** run on SSD nodes (hard rule) and **prefers** zone
`us-east-1a` (soft rule). It stays Pending if no SSD node exists.

```
   node-1 disktype=ssd, zone=us-east-1a   <== best: matches required + preferred
   node-2 disktype=ssd, zone=us-east-1b   <== ok: matches required only
   node-3 disktype=hdd                    x  excluded by the hard rule
```

```yaml
apiVersion: v1
kind: Pod
metadata: { name: ssd-pod }
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:   # HARD
        nodeSelectorTerms:
          - matchExpressions:
              - { key: disktype, operator: In, values: ["ssd"] }
      preferredDuringSchedulingIgnoredDuringExecution:  # SOFT
        - weight: 80
          preference:
            matchExpressions:
              - { key: zone, operator: In, values: ["us-east-1a"] }
  containers:
    - name: app
      image: nginx
```

```bash
kubectl label node node-1 disktype=ssd zone=us-east-1a
kubectl label node node-2 disktype=ssd zone=us-east-1b
kubectl apply -f ssd-pod.yaml
kubectl get pod ssd-pod -o wide          # expect node-1 (best match)
kubectl describe pod ssd-pod             # events explain Pending if no SSD node
```

## Key takeaways
- Node affinity = pod **chooses nodes** by labels, richer than `nodeSelector`.
- **required** = hard (Pending if unmet); **preferred** = soft (best-effort).
- Combine taints/tolerations + affinity to dedicate nodes properly.

## Checklist
- [ ] Labeled nodes and used a required nodeAffinity rule
- [ ] Saw a pod go Pending when no node matched
- [ ] Used a preferred rule with a weight
- [ ] Compared nodeSelector vs nodeAffinity
