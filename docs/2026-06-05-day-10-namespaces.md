# Day 10 — Kubernetes Namespaces

> Video: Day 10/40 — Kubernetes Namespace Explained
> https://www.youtube.com/watch?v=yVLXIydlU_0
> Duration: ~28 min

## What is a Namespace?
A **virtual cluster inside a cluster** — a logical boundary to group and isolate
resources (pods, services, configmaps...). Great for separating teams/envs.

```
   +================= ONE PHYSICAL CLUSTER =================+
   |                                                        |
   |  ns: dev            ns: staging         ns: prod       |
   |  +-------------+    +-------------+     +-------------+ |
   |  | pod web     |    | pod web     |     | pod web     | |
   |  | svc web     |    | svc web     |     | svc web     | |
   |  +-------------+    +-------------+     +-------------+ |
   |   names can repeat across namespaces (isolated)        |
   +========================================================+
```

## Default namespaces
```
   default          -> where your objects go if none specified
   kube-system      -> control-plane components (coredns, proxy...)
   kube-public      -> world-readable cluster info
   kube-node-lease  -> node heartbeat lease objects
```

## Why use them?
- **Isolation**: same names in different namespaces don't clash.
- **Access control**: scope RBAC roles per namespace.
- **Resource quotas**: cap CPU/memory per namespace.
- **Organization**: group by team / environment / app.

## Commands
```bash
kubectl get ns                                  # list namespaces
kubectl create namespace dev                    # create
kubectl get pods -n dev                          # list pods in ns
kubectl get pods --all-namespaces               # everything (-A)
kubectl run nginx --image=nginx -n dev          # create in ns

# set default ns for current context (stop typing -n)
kubectl config set-context --current --namespace=dev
```

## Namespace in YAML
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  namespace: dev        # <- pin the object to a namespace
spec:
  containers:
    - name: nginx
      image: nginx
```

## Cross-namespace DNS
```
   same ns:   curl web
   other ns:  curl web.dev.svc.cluster.local
              <service>.<namespace>.svc.cluster.local
```

## ResourceQuota (cap a namespace)
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    pods: "10"
    requests.cpu: "2"
    requests.memory: 2Gi
```

## Not namespaced
Some objects are **cluster-scoped** (not in any namespace):
```
   nodes, namespaces, persistentvolumes, clusterroles
   check: kubectl api-resources --namespaced=false
```

## Key takeaways
- Namespaces = logical isolation within one cluster.
- Names are unique **per namespace**, not cluster-wide.
- Use `-n <ns>` / `-A`, and cross-ns DNS = `svc.ns.svc.cluster.local`.

## Checklist
- [ ] Created a namespace and ran a pod in it
- [ ] Listed resources with `-n` and `-A`
- [ ] Set a default namespace on the context
- [ ] Reached a service across namespaces by FQDN
