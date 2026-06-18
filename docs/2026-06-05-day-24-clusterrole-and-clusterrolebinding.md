# Day 24 — ClusterRole and ClusterRoleBinding

> Video: Day 24/40 — Kubernetes RBAC Continued (ClusterRole & ClusterRoleBinding)
> https://www.youtube.com/watch?v=DswQe7shSa4
> Duration: ~15 min

## Problem & solution
Namespaced Roles can't grant access to cluster-scoped resources (nodes, PVs,
namespaces, CSRs) or apply across all namespaces at once. Cluster-wide
permissions need a cluster-scoped RBAC mechanism.

**Solution:** Use a ClusterRole + ClusterRoleBinding for cluster-scoped resources (nodes, PVs) or to grant the same permissions across all namespaces.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------ CLUSTER -------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+   |
   | | +------------+   +------+   +-----------+   +----------------+ |   |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |   |
   | | +------------+   +------+   +-----------+   +----------------+ |   |
   | | api-server  <== ClusterRole spans ALL namespaces               |   |
   | +----------------------------------------------------------------+   |
   | +--------- WORKER NODE   (kubelet | kube-proxy | runtime) ---------+ |
   | |    <== nodes are cluster-scoped (only a ClusterRole grants them) | |
   | | + namespace: default +                                           | |
   | | | +----- POD -----+  |                                           | |
   | | | | + CONTAINER + |  |                                           | |
   | | | | | app       | |  |                                           | |
   | | | | +-----------+ |  |                                           | |
   | | | +---------------+  |                                           | |
   | | +--------------------+                                           | |
   | +------------------------------------------------------------------+ |
   +----------------------------------------------------------------------+
```

## Why we need cluster-scoped RBAC
Role/RoleBinding (Day 23) are **namespaced** — they can't grant access to:
```
   - cluster-scoped resources: nodes, persistentvolumes, namespaces, CSRs
   - resources across ALL namespaces at once
```
`ClusterRole` + `ClusterRoleBinding` solve exactly that.

## Namespaced vs cluster-scoped (the whole map)
RBAC has **two tiers**: namespaced objects (Role + RoleBinding) and cluster-wide
objects (ClusterRole + ClusterRoleBinding). The binding decides the scope.

```
   SCOPE        PERMISSIONS        BINDING
   namespace    Role               RoleBinding         -> one namespace
   cluster      ClusterRole        ClusterRoleBinding  -> whole cluster
```

```
   Role         -> verbs on namespaced resources, in ONE namespace
   ClusterRole  -> verbs on cluster-scoped resources, OR namespaced
                   resources across EVERY namespace
```

> Trick: a **ClusterRole** can be reused by a **RoleBinding** to grant it in just
> one namespace — write the permission once, scope it where you like.

## Which resources are cluster-scoped?
Ask the API which resources live outside namespaces — those are the ones that
require a **ClusterRole** to grant access.

```bash
kubectl api-resources --namespaced=false    # cluster-scoped (nodes, pv, ns...)
kubectl api-resources --namespaced=true     # namespaced (pods, svc, cm...)
```

## ClusterRole (the permissions)
A **ClusterRole** defines a set of verbs on resources, just like a Role, but it
is not tied to any namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch"]
```

## ClusterRoleBinding (attach to a user, cluster-wide)
A **ClusterRoleBinding** attaches a ClusterRole to a subject across the entire
cluster, every namespace included.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: node-reader-binding
subjects:
  - kind: User
    name: adam
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

## Imperative shortcuts
The same objects can be created in one line with `kubectl create`, handy in the
exam and for quick experiments.

```bash
kubectl create clusterrole node-reader \
  --verb=get,list,watch --resource=nodes

kubectl create clusterrolebinding node-reader-binding \
  --clusterrole=node-reader --user=adam
```

## Verify
Use `kubectl auth can-i` with `--as` to confirm the binding actually grants the
access you intended.

```bash
kubectl auth can-i list nodes --as adam        # -> yes (cluster-wide)
kubectl auth can-i get pods  --as adam -A      # only if also granted
```

## Built-in ClusterRoles worth knowing
Kubernetes ships with default ClusterRoles you can bind directly instead of
writing your own.

```
   cluster-admin -> god mode (all verbs, all resources) — handle with care
   admin / edit  -> common namespace-level roles (used via RoleBinding)
   view          -> read-only
```

## End-to-end example: listing cluster-scoped nodes
Nodes live outside any namespace, so only a ClusterRole can grant access.

```
   +-----+        +------------+
   | amy |        | api-server |
   +-----+        +------------+
      |                  |
      | (1) kubectl get nodes   (nodes are cluster-scoped)
      |----------------->|
      |                  |
     (2) AUTHN: user=amy |
      |                  |
     (3) AUTHZ: a namespaced Role can NEVER grant 'nodes'
      |                  |
     (4) ClusterRoleBinding -> ClusterRole 'node-reader' (get/list nodes)
      |                  |
      | (5) 200 OK -> all nodes listed (cluster-wide)
      |<-----------------|
      |                  |
   Cluster-scoped resources (nodes, PVs, namespaces) need a ClusterRole.
```

## Key takeaways
- **ClusterRole/ClusterRoleBinding = cluster-wide RBAC.**
- Needed for cluster-scoped resources (nodes, PVs, namespaces, CSRs) and for
  granting access across **all** namespaces.
- A ClusterRole can be bound by a **RoleBinding** to limit it to one namespace.
- Use `kubectl api-resources --namespaced=false` to see what's cluster-scoped.

## Checklist
- [ ] Listed cluster-scoped resources with `api-resources --namespaced=false`
- [ ] Created a `node-reader` ClusterRole + ClusterRoleBinding
- [ ] Verified `kubectl auth can-i list nodes --as adam`
- [ ] Understand reusing a ClusterRole via a RoleBinding for one namespace
