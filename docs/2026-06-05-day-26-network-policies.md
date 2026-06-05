# Day 26 — Network Policies

> Video: Day 26/40 — Kubernetes Network Policies Explained
> https://www.youtube.com/watch?v=eVtnevr3Rao
> Duration: ~26 min

## The default: everything can talk to everything
By default Kubernetes networking is **flat and open** — any pod can reach any
other pod. A **NetworkPolicy** is a firewall for pods that restricts this.

```
   No policy:                With policy (db allows only backend):
   frontend -> backend       frontend  x-> db   (blocked)
   frontend -> db            backend   --> db   (allowed :3306)
   backend  -> db            frontend  --> backend (still allowed)
```

## You need a CNI that ENFORCES policy
`NetworkPolicy` objects are inert unless the CNI plugin implements them.
The default **kindnet** does NOT — use **Calico** (or Cilium, etc).

```yaml
# kind cluster with default CNI disabled, so we can install Calico
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
networking:
  disableDefaultCNI: true
  podSubnet: 192.168.0.0/16
```
> Then install Calico (docs.tigera.io/calico .../kind). Without an enforcing CNI,
> your policies are silently ignored.

## Direction: Ingress vs Egress
A policy controls **inbound** traffic, **outbound** traffic, or both, declared in
`policyTypes`.

```
   Ingress -> traffic INTO the selected pods
   Egress  -> traffic OUT of the selected pods
   policyTypes lists which directions this policy controls
```

## How selection works
A policy uses **label selectors** to pick the target pods and to describe which
peers and ports are allowed.

```
   podSelector   -> which pods THIS policy applies to (the target)
   from / to     -> the allowed peers (podSelector / namespaceSelector / ipBlock)
   ports         -> which ports/protocols are allowed
```

> Key rule: as soon as a pod is selected by ANY policy for a direction, it
> becomes **default-deny** for that direction — only the listed traffic is allowed.

## Example: only backend may reach mysql on 3306
This **ingress** policy targets the db pods and allows traffic only from pods
labelled `role=backend` on port 3306.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-test
spec:
  podSelector:
    matchLabels:
      name: mysql            # applies to the db pods
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: backend  # only pods labelled role=backend
      ports:
        - port: 3306
```
Result: `backend -> mysql:3306` allowed; `frontend -> mysql` blocked.

## Default-deny everything (common baseline)
Selecting **all pods** with no rules creates a deny-all baseline you then open up
with additive allow policies.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}            # all pods in the namespace
  policyTypes:
    - Ingress
  # no ingress rules = deny all inbound
```

## Test it
Exec into pods on either side and `curl` the db to confirm allowed traffic
connects and blocked traffic hangs.

```bash
# from a backend pod (should work), then a frontend pod (should hang/fail)
kubectl exec -it backend  -- curl -m 3 db:3306
kubectl exec -it frontend -- curl -m 3 db:3306
```

## Key takeaways
- Pods are **open by default**; NetworkPolicy adds a firewall.
- Needs an **enforcing CNI** (Calico) — kindnet ignores policies.
- `podSelector` picks the target; `from`/`to` + `ports` allow specific peers.
- Selecting a pod for a direction makes it **default-deny** for that direction.
- Policies are **additive** (allow-only); combine them per namespace.

## Checklist
- [ ] Created a kind cluster with default CNI disabled + installed Calico
- [ ] Deployed frontend/backend/mysql and confirmed open connectivity
- [ ] Applied the `db-test` policy and verified only backend reaches mysql
- [ ] Tried a `default-deny-ingress` baseline and saw traffic blocked
