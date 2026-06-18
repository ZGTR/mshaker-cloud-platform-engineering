# Day 22 — Authentication and Authorization

> Video: Day 22/40 — Kubernetes Authentication and Authorization Simply Explained
> https://www.youtube.com/watch?v=P0bogYEyfeI
> Duration: ~18 min

## Key terms
| Term | Meaning |
| --- | --- |
| Authentication (AuthN) | Proving who you are |
| Authorization (AuthZ) | Deciding what you may do |
| RBAC | Role-based access control authorizer |
| ServiceAccount | Identity for in-cluster workloads |
| Bearer token | Credential that proves an identity |
| `kubectl auth can-i` | Checks whether an action is allowed |
| Admission | Post-authz request validation/mutation |

## Problem & solution
An API that anyone could call and do anything on would be catastrophic. Every
request must prove who it is (authentication) and be checked for what it's
allowed to do (authorization) before it takes effect.

**Solution:** Make every request pass authentication (certs/tokens), then authorization (RBAC), then admission control before it is stored.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== every request: authn -> authz -> admission     | |
   | +----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                 |
   | | + namespace: default +                         |                 |
   | | | +----- POD -----+  |                         |                 |
   | | | | + CONTAINER + |  |                         |                 |
   | | | | | app       | |  |                         |                 |
   | | | | +-----------+ |  |                         |                 |
   | | | +---------------+  |                         |                 |
   | | +--------------------+                         |                 |
   | +------------------------------------------------+                 |
   +--------------------------------------------------------------------+
```

## Two gates every request passes
Every API call runs a fixed gauntlet: it is first authenticated, then
authorized, then checked by admission control before being stored.

```
   request -> [ AUTHENTICATION ]  who are you?      -> identity
           -> [ AUTHORIZATION  ]  what can you do?   -> allow / deny
           -> [ Admission ]       extra policy checks -> mutate/validate
           -> persisted in etcd
```

> **AuthN = identity. AuthZ = permission.** You can be authenticated and still
> get a `Forbidden` because you are not authorized.

## Authentication: proving WHO you are
The API server has **no user database**. Identity comes from:
```
   - client CERTIFICATES (CN = user, O = group)   <- common
   - bearer TOKENS (service accounts, OIDC)
   - static token / basic auth files (rarely, legacy)
```

Your `kubeconfig` is basically your **keycard**: it holds the server address,
the CA to trust, and your client cert/key (or token).

```bash
kubectl get pods --kubeconfig config   # use a specific kubeconfig
kubectl get pods                       # defaults to ~/.kube/config
```

Raw API call with explicit creds (what kubeconfig does under the hood):
```bash
kubectl get --raw /api/v1/namespaces/default/pods \
  --server https://localhost:64418 \
  --client-key adam.key \
  --client-certificate adam.crt \
  --certificate-authority ca.crt
```

## Authorization: what you can DO
After identity is known, the API server checks **authorization modules** in a
configured order; the first to decide wins:

```
   Node     -> authorizes kubelets to access what their node needs
   ABAC     -> attribute-based, file of policies (hard to manage)
   RBAC     -> role-based, the RECOMMENDED approach (Day 23-24)
   Webhook  -> delegate to an external service (e.g. OPA)
```

> `AlwaysAllow` / `AlwaysDeny` modes exist but are for **testing only**.

## Check your own access
These commands let you ask the API server who you are and whether a given action
is permitted, optionally impersonating another user.

```bash
kubectl auth whoami                 # who the API server thinks you are
kubectl auth can-i create pods                  # for yourself
kubectl auth can-i delete nodes --as adam       # impersonate to test
kubectl auth can-i '*' '*'                       # am I admin?
```

## The mental model
Putting it together, a request flows from your kubeconfig credentials through
authentication, authorization, and admission before the action runs.

```
   kubeconfig (cert/token)  --AuthN-->  "you are adam"
                            --AuthZ-->  RBAC: "adam may get pods in default"
                            --Admit-->  policies pass
                            --> action performed
```

## End-to-end example: a kubectl request from laptop to etcd
Follow one `kubectl apply` through every gate the API server runs.

```
   +---------+        +------------+        +------+
   | kubectl |        | api-server |        | etcd |
   +---------+        +------------+        +------+
        |                    |                  |
        | (1) kubectl apply -f pod.yaml  (TLS: client cert)
        |------------------->|                  |
        |                    |                  |
     (2) AUTHN : cert CN=adam, O=devs        -> user 'adam'
        |                    |                  |
     (3) AUTHZ : RBAC -> may adam create pods in 'default'?
        |                    |                  |
     (4) ADMISSION : quotas / policies / defaulting
        |                    |                  |
        |                    | (5) persist the Pod object
        |                    |----------------->|
        |                    |                  |
        |                    | (6) stored (resourceVersion)
        |                    |<-----------------|
        |                    |                  |
        | (7) 201 Created    |                  |
        |<-------------------|                  |
        |                    |                  |
   403 Forbidden at step 3 -> NOTHING is written; identity was fine,
   the permission was not. AuthN and AuthZ are two separate gates.
```

## Key takeaways
- Every request is **authenticated then authorized** (then admission).
- API server has no user store — identity comes from **certs or tokens**.
- `kubeconfig` carries server + CA + your credentials.
- Authorization order: **Node -> RBAC -> Webhook**; RBAC is what you'll use.
- Use `kubectl auth can-i ... --as <user>` to test permissions.

## Checklist
- [ ] Can explain AuthN vs AuthZ in one sentence each
- [ ] Inspected `~/.kube/config` and identified server/CA/credentials
- [ ] Made a `--raw` API call with explicit cert flags
- [ ] Used `kubectl auth can-i` with `--as` to test access
