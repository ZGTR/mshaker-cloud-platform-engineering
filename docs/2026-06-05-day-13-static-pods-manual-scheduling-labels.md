# Day 13 — Static Pods, Manual Scheduling, Labels & Selectors

> Video: Day 13/40 — Static Pods, Manual Scheduling, Labels, and Selectors
> https://www.youtube.com/watch?v=6eGf7_VSbrQ
> Duration: ~30 min

## Static Pods — managed by kubelet, not the API server

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
```
   Service        -> selects which pods to route to
   Deployment/RS  -> selects which pods it owns
   NetworkPolicy  -> selects which pods a rule applies to
   nodeSelector   -> pod picks nodes by node labels
```

## nodeSelector (simple node targeting)
```yaml
spec:
  nodeSelector:
    disktype: ssd      # only schedule on nodes labeled disktype=ssd
```
```bash
kubectl label node cka-worker disktype=ssd
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
