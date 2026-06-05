# Day 25 — Service Accounts

> Video: Day 25/40 — Kubernetes Service Account (RBAC Continued)
> https://www.youtube.com/watch?v=k2iCq7IlMKM
> Duration: ~16 min

## Two kinds of accounts
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
```bash
kubectl create token build-bot                 # short-lived token (on demand)
kubectl create token build-bot --duration=1h
```
> Modern Kubernetes uses **short-lived, auto-rotated projected tokens** instead
> of the old permanent Secret-based tokens.

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
