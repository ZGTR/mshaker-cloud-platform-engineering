# Day 10 — Kubernetes Namespaces

> Video: Day 10/40 — Kubernetes Namespace Explained
> https://www.youtube.com/watch?v=yVLXIydlU_0
> Duration: ~28 min

## Problem & solution
Putting every team and environment in one shared space causes name collisions,
no isolation, and no way to scope quotas or access. We need logical boundaries
inside a single physical cluster.

**Solution:** Partition the cluster into namespaces (dev/staging/prod) for isolation, resource quotas, and scoped RBAC.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | +----------------------------------------------------------------+ |
   | +- WORKER NODE   (kubelet | kube-proxy | runtime) --+              |
   | | +------------- namespace: default --------------+ |              |
   | | | +----- POD -----+                             | |              |
   | | | | + CONTAINER + |                             | |              |
   | | | | | app       | |                             | |              |
   | | | | +-----------+ |                             | |              |
   | | | +---------------+                             | |              |
   | | |    <== logical boundary: dev / staging / prod | |              |
   | | +-----------------------------------------------+ |              |
   | +---------------------------------------------------+              |
   +--------------------------------------------------------------------+
```

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
A fresh cluster ships with four namespaces, each with a job.

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
The core commands for creating namespaces and scoping kubectl to one with `-n`.

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
Set `metadata.namespace` to pin an object to a specific namespace instead of
`default`.

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

## Worked example: svc-test vs svc-demo
The demo runs the **same nginx workload twice**, once per namespace, each fronted
by its own service. It shows isolation *and* how to cross the boundary.

```
   +-------------------- ip address --------------------+
   |                                                    |
   | ns: default                  ns: demo              |
   | +------------+               +------------+        |
   | | nginx      |   svc-test    |  svc-demo  | nginx  |
   | | nginx <----+---------------+----------> | nginx  |
   | | nginx      |   (ClusterIP) | (ClusterIP)| nginx  |
   | +------------+               +------------+        |
   +----------------------------------------------------+
```

- **svc-test** lives in `default` and load-balances the 3 nginx pods there.
- **svc-demo** lives in `demo` and load-balances the 3 nginx pods there.
- Both services can be named the same kind of thing without clashing — names are
  unique **per namespace**, so the two never collide.
- A pod in `default` hitting `svc-test` uses the **short name** (same namespace).
- To reach across, a pod in `default` calls `svc-demo` by its **FQDN**, and a pod
  in `demo` calls `svc-test` by its FQDN. The arrow crossing the boundary in the
  diagram is exactly this cross-namespace call.

```bash
kubectl create namespace demo
kubectl run nginx --image=nginx -n default          # x3 -> behind svc-test
kubectl run nginx --image=nginx -n demo             # x3 -> behind svc-demo
kubectl expose pod nginx --name=svc-test -n default --port=80
kubectl expose pod nginx --name=svc-demo -n demo   --port=80

# from a pod in default:
curl svc-test                                       # short name, same ns
curl svc-demo.demo.svc.cluster.local                # FQDN, cross ns
```

Each service still gets its **own ClusterIP**; the FQDN just resolves to that IP
through CoreDNS. Namespaces don't block traffic by default — they scope *names*,
not the network (that's what NetworkPolicies are for).

## Cross-namespace DNS
A pod reaches a service in **another namespace** by using its fully-qualified DNS
name; same-namespace calls can use the short name.

```
   same ns:   curl web
   other ns:  curl web.dev.svc.cluster.local
              <service>.<namespace>.svc.cluster.local
```

## ResourceQuota (cap a namespace)
A **ResourceQuota** caps how much CPU, memory, and how many objects a namespace
can consume.

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
