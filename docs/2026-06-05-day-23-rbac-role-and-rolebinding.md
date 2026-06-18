# Day 23 — RBAC: Role and RoleBinding

> Video: Day 23/40 — Kubernetes RBAC Explained (Role Based Access Control)
> https://www.youtube.com/watch?v=uGcDt7iNFkE
> Duration: ~22 min

## Key terms
| Term | Meaning |
| --- | --- |
| RBAC | Role-based access control |
| Role | A namespaced permission set |
| RoleBinding | Grants a Role to a subject in a namespace |
| Verb | The action (get/list/create/...) |
| Resource | The object type a rule covers |
| apiGroup | The API family a resource belongs to |
| Subject | The user/group/ServiceAccount being granted |

## Problem & solution
Once requests are authenticated, you need a precise, auditable way to grant
least-privilege permissions within a namespace instead of all-or-nothing
access. Roles and RoleBindings define exactly who can do what.

**Solution:** Grant least-privilege access with a namespaced Role (verbs x resources) bound to a user or group via a RoleBinding.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== RBAC authorizes verbs on resources             | |
   | +----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                 |
   | | +----------- namespace: default -----------+   |                 |
   | | | +----- POD -----+                        |   |                 |
   | | | | + CONTAINER + |                        |   |                 |
   | | | | | app       | |                        |   |                 |
   | | | | +-----------+ |                        |   |                 |
   | | | +---------------+                        |   |                 |
   | | |    <== Role + RoleBinding are namespaced |   |                 |
   | | +------------------------------------------+   |                 |
   | +------------------------------------------------+                 |
   +--------------------------------------------------------------------+
```

## The idea
RBAC answers **"what can this identity do?"** with two halves:
```
   ROLE         -> a set of PERMISSIONS (verbs on resources)  [namespaced]
   ROLEBINDING  -> ATTACHES a Role to a user / group / SA
```

```
   [user: krishna]  --RoleBinding-->  [Role: pod-reader]
                                        verbs: get,list,watch
                                        resources: pods
                                        namespace: default
```

> A Role grants nothing by itself until a **RoleBinding** connects it to someone.
> Both are **namespaced** (cluster-wide equivalents = Day 24).

## Permission = verbs x resources x apiGroups
A single rule is the combination of which **verbs** are allowed on which
**resources** in which **apiGroups**.

```
   verbs:      get list watch create update patch delete
   resources:  pods deployments services configmaps ...
   apiGroups:  "" (core: pods, svc), "apps" (deployments), etc.
```

## First, create a user (cert) — recap of Day 21/23
Before binding permissions you need an identity, so generate the user's cert via
the CSR flow from Day 21.

```bash
openssl genrsa -out krishna.key 2048
openssl req -new -key krishna.key -out krishna.csr -subj "/CN=krishna"
# submit CSR -> approve -> pull signed cert:
kubectl get csr krishna -o jsonpath='{.status.certificate}' | base64 -d > krishna.crt
```

## Role (the permissions)
The **Role** defines what may be done, here allowing read-only access to pods in
the `default` namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
  - apiGroups: [""]            # "" = core API group
    resources: ["pods"]
    verbs: ["get", "watch", "list"]
```

## RoleBinding (attach Role to the user)
The **RoleBinding** is what actually grants the permissions, connecting the Role
to a specific subject such as our user.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
  - kind: User
    name: krishna             # case-sensitive; must match CN
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role                  # Role or ClusterRole
  name: pod-reader            # must match the Role name above
  apiGroup: rbac.authorization.k8s.io
```

## Imperative shortcuts
The same Role and RoleBinding can be created in one command each, without
writing YAML.

```bash
kubectl create role pod-reader \
  --verb=get,list,watch --resource=pods -n default

kubectl create rolebinding read-pods \
  --role=pod-reader --user=krishna -n default
```

## Verify
Confirm the binding works by impersonating the user and checking both an allowed
and a denied action.

```bash
kubectl auth whoami
kubectl auth can-i list pods                    # as yourself (admin -> yes)
kubectl auth can-i list pods --as krishna       # -> yes (in default)
kubectl auth can-i delete pods --as krishna     # -> no (not granted)
kubectl auth can-i list pods --as krishna -n kube-system   # -> no (other ns)
```

## End-to-end example: amy reads pods in one namespace only
A namespaced Role + RoleBinding lets amy work in `dev` but nowhere else.

```
   +-----+        +------------+
   | amy |        | api-server |
   +-----+        +------------+
      |                  |
      | (1) kubectl get pods -n dev   (cert O=dev-team)
      |----------------->|
      |                  |
     (2) AUTHN: user=amy, group=dev-team
      |                  |
     (3) AUTHZ: RoleBinding in 'dev' -> Role 'pod-reader' (get/list pods)
      |                  |
      | (4) 200 OK -> pods in dev listed
      |<-----------------|
      |                  |
      | (5) kubectl get pods -n prod
      |----------------->|
      |                  |
     (6) no RoleBinding for amy in 'prod'
      |                  |
      | (7) 403 Forbidden|
      |<-----------------|
      |                  |
   Role + RoleBinding are NAMESPACED: power in 'dev' grants nothing in 'prod'.
```

## Key takeaways
- **Role = permissions, RoleBinding = who gets them.** Both namespaced.
- A rule is **verbs x resources x apiGroups**; core group is `""`.
- Subject `name` must match the cert `CN` exactly (case-sensitive).
- Test with `kubectl auth can-i <verb> <resource> --as <user>`.

## Checklist
- [ ] Created the `krishna` user cert via CSR
- [ ] Created a `pod-reader` Role and a `read-pods` RoleBinding
- [ ] Verified access with `--as krishna` (allowed verb + denied verb)
- [ ] Confirmed the binding is scoped to its namespace only
