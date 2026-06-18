# Day 25 — Service Accounts

> Video: Day 25/40 — Kubernetes Service Account (RBAC Continued)
> https://www.youtube.com/watch?v=k2iCq7IlMKM
> Duration: ~16 min

## Key terms
| Term | Meaning |
| --- | --- |
| ServiceAccount (SA) | Identity for pods/workloads |
| default SA | Auto-assigned account per namespace |
| Token | Credential mounted into a pod |
| Projected token | Short-lived, audience-bound token |
| automountServiceAccountToken | Toggle for mounting the token |
| RBAC | Binds permissions to a ServiceAccount |

## Problem & solution
Pods, controllers, and CI bots also need an identity to call the API, but human
user accounts aren't Kubernetes objects and don't fit automated workloads.
Service accounts give non-human workloads a managed in-cluster identity.

**Solution:** Give in-cluster apps a ServiceAccount identity with an auto-mounted token, then grant it permissions through RBAC.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== validates the ServiceAccount token             | |
   | +----------------------------------------------------------------+ |
   | +- WORKER NODE   (kubelet | kube-proxy | runtime) -+               |
   | | +------------- namespace: default -------------+ |               |
   | | | +------------------ POD -------------------+ | |               |
   | | | | + CONTAINER +                            | | |               |
   | | | | | app       |                            | | |               |
   | | | | +-----------+                            | | |               |
   | | | |    <== runs as a ServiceAccount identity | | |               |
   | | | +------------------------------------------+ | |               |
   | | +----------------------------------------------+ |               |
   | +--------------------------------------------------+               |
   +--------------------------------------------------------------------+
```

## Two kinds of accounts
Kubernetes splits identities into **user accounts** for humans and
**service accounts** for workloads — only the latter is a real cluster object.

```
   USER account      -> humans: admins, developers, operators
                        (certs/OIDC, NOT a Kubernetes object)
   SERVICE account   -> non-humans: pods, controllers, CI bots, apps
                        (a real Kubernetes object you can create)
```

> When **code inside a pod** needs to call the Kubernetes API, it uses a
> **ServiceAccount**, not a human user cert.

## Default service account
Every namespace has a `default` SA, and every pod that doesn't name one gets it
mounted automatically.

```bash
kubectl get sa                       # SAs in current namespace
kubectl get sa -A                    # every namespace has its own 'default'
```

## Create a service account
A **ServiceAccount** is a namespaced object you create like any other resource.

```bash
kubectl create sa build-bot
kubectl get sa build-bot -o yaml
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: build-bot
  namespace: default
```

## Give it permissions (RBAC, same as users)
A SA is just another **subject** in a RoleBinding/ClusterRoleBinding.
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: build-bot-read
  namespace: default
subjects:
  - kind: ServiceAccount
    name: build-bot
    namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

Verify with impersonation:
```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:default:build-bot     # -> yes
```

## Use it from a pod
Set `serviceAccountName` on the pod spec so the container runs as that SA and
gets its token mounted.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  serviceAccountName: build-bot         # <- pod runs as this SA
  containers:
    - name: app
      image: nginx
```

The token is mounted at:
```
   /var/run/secrets/kubernetes.io/serviceaccount/
     token       -> JWT bearer token (auto-rotated, projected)
     ca.crt      -> cluster CA to trust the API server
     namespace   -> the pod's namespace
```

## Tokens
You can mint a bearer token for a SA on demand, useful for testing API calls or
external clients.

```bash
kubectl create token build-bot                 # short-lived token (on demand)
kubectl create token build-bot --duration=1h
```
> Modern Kubernetes uses **short-lived, auto-rotated projected tokens** instead
> of the old permanent Secret-based tokens.

## End-to-end example: a pod calls the API as its ServiceAccount
The app inside a pod authenticates with its auto-mounted SA token.

```
   +---------+        +------------+
   | pod-app |        | api-server |
   +---------+        +------------+
        |                    |
     (0) pod runs as ServiceAccount 'reader' (token auto-mounted)
        |                    |
        | (1) GET /api/v1/.../pods  Authorization: Bearer <token>
        |------------------->|
        |                    |
     (2) AUTHN: token -> system:serviceaccount:default:reader
        |                    |
     (3) AUTHZ: RoleBinding -> Role allows get/list pods
        |                    |
        | (4) 200 OK -> pod list
        |<-------------------|
        |                    |
   In-cluster apps authenticate as a ServiceAccount, never as a human user.
```

## Key takeaways
- **User accounts = humans, ServiceAccounts = workloads/bots.**
- SAs are real namespaced objects; each namespace has a `default` SA.
- Grant a SA access with the **same RBAC** (Role/ClusterRole + binding).
- Subject form: `system:serviceaccount:<namespace>:<name>`.
- Pods authenticate using the projected token mounted into the container.

## Checklist
- [ ] Listed default SAs across namespaces
- [ ] Created a `build-bot` SA and bound it to a Role
- [ ] Verified with `--as=system:serviceaccount:default:build-bot`
- [ ] Ran a pod with `serviceAccountName` and found the mounted token
