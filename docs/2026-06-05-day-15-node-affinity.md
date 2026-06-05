# Day 15 — Node Affinity

> Video: Day 15/40 — Kubernetes Node Affinity Explained
> https://www.youtube.com/watch?v=5vimzBRnoDk
> Duration: ~27 min

## What is Node Affinity?
A richer, more expressive way for a **pod to choose which nodes** it can run on,
based on **node labels**. It's the upgrade to the simple `nodeSelector`.

```
   nodeSelector  -> exact match only (disktype=ssd)
   nodeAffinity  -> operators (In, NotIn, Exists...), AND required vs preferred
```

## Attract vs repel (vs Day 14)
```
   Taint/Toleration -> NODE repels pods (permission to land)
   Node Affinity    -> POD is drawn to matching nodes (preference/requirement)
```

## The two flavors

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
```
   In        label value is in the list
   NotIn     label value is NOT in the list  (anti-affinity-ish)
   Exists    label key exists (any value)
   DoesNotExist  label key absent
   Gt / Lt   greater/less than (numeric)
```

## Setup: label your nodes
```bash
kubectl label node cka-worker disktype=ssd
kubectl get nodes --show-labels
kubectl get nodes -l disktype=ssd
```

## Verify scheduling
```bash
kubectl apply -f ssd-pod.yaml
kubectl get pod ssd-pod -o wide        # which node did it land on?
kubectl describe pod ssd-pod           # events explain Pending if no match
```

## nodeSelector vs nodeAffinity
| | nodeSelector | nodeAffinity |
|---|--------------|--------------|
| Syntax | simple map | expressions + operators |
| Hard/soft | hard only | required (hard) + preferred (soft) |
| Power | exact match | In/NotIn/Exists/Gt/Lt |

## Best practice: combine with taints
```
   Taint node (repel everyone) + Toleration (let my pod in) +
   Node Affinity (force my pod TO that node) = truly dedicated node.
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
