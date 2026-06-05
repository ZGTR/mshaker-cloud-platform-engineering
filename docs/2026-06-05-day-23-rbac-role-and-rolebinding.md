# Day 23 — RBAC: Role and RoleBinding

> Video: Day 23/40 — Kubernetes RBAC Explained (Role Based Access Control)
> https://www.youtube.com/watch?v=uGcDt7iNFkE
> Duration: ~22 min

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
```
   verbs:      get list watch create update patch delete
   resources:  pods deployments services configmaps ...
   apiGroups:  "" (core: pods, svc), "apps" (deployments), etc.
```

## First, create a user (cert) — recap of Day 21/23
```bash
openssl genrsa -out krishna.key 2048
openssl req -new -key krishna.key -out krishna.csr -subj "/CN=krishna"
# submit CSR -> approve -> pull signed cert:
kubectl get csr krishna -o jsonpath='{.status.certificate}' | base64 -d > krishna.crt
```

## Role (the permissions)
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
```bash
kubectl create role pod-reader \
  --verb=get,list,watch --resource=pods -n default

kubectl create rolebinding read-pods \
  --role=pod-reader --user=krishna -n default
```

## Verify
```bash
kubectl auth whoami
kubectl auth can-i list pods                    # as yourself (admin -> yes)
kubectl auth can-i list pods --as krishna       # -> yes (in default)
kubectl auth can-i delete pods --as krishna     # -> no (not granted)
kubectl auth can-i list pods --as krishna -n kube-system   # -> no (other ns)
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
