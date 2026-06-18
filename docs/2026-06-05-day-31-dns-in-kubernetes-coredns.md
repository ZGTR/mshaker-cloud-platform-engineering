# Day 31 — DNS in Kubernetes (CoreDNS)

> Video: Day 31/40 — DNS in Kubernetes
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Problem & solution
Pod IPs are ephemeral — they change on every restart, scale, or reschedule.
Hard-coding them is impossible. Kubernetes runs an in-cluster DNS (**CoreDNS**)
so workloads can reach each other by **stable names** like
`payments.prod.svc.cluster.local` instead of chasing IPs.

**Solution:** Run CoreDNS in-cluster so pods reach Services by stable DNS names (<svc>.<ns>.svc.cluster.local) via the resolver in their /etc/resolv.conf.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== CoreDNS watches Services + Endpoints here      | |
   | +----------------------------------------------------------------+ |
   | +----- WORKER NODE   (kubelet | kube-proxy | runtime) -----+       |
   | | +----------------- namespace: default -----------------+ |       |
   | | | +----- POD -----+                                    | |       |
   | | | | + CONTAINER + |                                    | |       |
   | | | | | app       | |                                    | |       |
   | | | | +-----------+ |                                    | |       |
   | | | +---------------+                                    | |       |
   | | |    <== each pod's /etc/resolv.conf points at CoreDNS | |       |
   | | +------------------------------------------------------+ |       |
   | +----------------------------------------------------------+       |
   +--------------------------------------------------------------------+
```

## What CoreDNS is
CoreDNS is a DNS server that runs **as pods** (a Deployment in `kube-system`),
fronted by a Service called `kube-dns`. It **watches the api-server** for
Services and Endpoints and answers cluster queries from that live data.

```bash
kubectl -n kube-system get deploy,pods -l k8s-app=kube-dns
kubectl -n kube-system get svc kube-dns          # the ClusterIP pods point at
kubectl -n kube-system get configmap coredns -o yaml   # the Corefile
```

## The naming scheme
Every Service gets a deterministic DNS name:

```
   <service>.<namespace>.svc.cluster.local        ->  Service ClusterIP
   <service>.<namespace>                            ->  same (search domain fills the rest)

   # headless Service (clusterIP: None) returns the POD IPs directly:
   <pod-hostname>.<service>.<namespace>.svc.cluster.local

   examples:
     payments.prod.svc.cluster.local
     kubernetes.default.svc.cluster.local   (the api-server itself)
```

## How a pod is wired for DNS
The kubelet writes each pod's `/etc/resolv.conf` to point at the CoreDNS
ClusterIP, with a `search` list and an `ndots` setting.

```bash
kubectl exec -it mypod -- cat /etc/resolv.conf
# nameserver 10.96.0.10
# search default.svc.cluster.local svc.cluster.local cluster.local
# options ndots:5
```
> `ndots:5` means names with **fewer than 5 dots** are tried against each
> `search` domain first. That is why `payments` resolves to
> `payments.<ns>.svc.cluster.local` — but it also causes extra lookups for
> external names (see pitfalls).

## End-to-end: one pod calls another by name
```
   +-----+        +---------+        +------------+
   | pod |        | CoreDNS |        | api-server |
   +-----+        +---------+        +------------+
      |                |                    |
      | (1) resolve my-svc.dev.svc.cluster.local
      |--------------->|                    |
      |                |                    |
     (2) CoreDNS watches Services + Endpoints from the api-server
      |                |                    |
      | (3) answer: ClusterIP 10.96.12.7    |
      |<---------------|                    |
      |                |                    |
     (4) pod connects to the ClusterIP; kube-proxy load-balances to a real pod
      |                |                    |
   Pods get /etc/resolv.conf pointing at the CoreDNS (kube-dns) ClusterIP.
```

## Test DNS from inside the cluster
```bash
# one-off debug pod
kubectl run dns-test --image=busybox:1.36 --restart=Never -it --rm -- \
  nslookup kubernetes.default

# from an existing pod
kubectl exec -it mypod -- nslookup payments.prod
kubectl exec -it mypod -- nslookup payments.prod.svc.cluster.local
```

## Common pitfalls
```
   - CoreDNS pods CrashLooping  -> often a bad Corefile or a node-resolv.conf loop
   - slow external lookups      -> ndots:5 tries search domains first; use a
                                    trailing dot ("github.com.") or set ndots:1
                                    via dnsConfig for chatty external clients
   - NXDOMAIN for a Service     -> wrong namespace, or no Endpoints (no ready pods)
   - headless Service confusion -> clusterIP:None returns POD IPs, not one VIP
   - NetworkPolicy too strict   -> blocks egress to kube-dns (allow UDP/TCP 53)
```

## Key takeaways
- **CoreDNS** (pods in `kube-system`, Service `kube-dns`) is the cluster resolver.
- It **watches the api-server** for Services/Endpoints — DNS reflects live state.
- Service name = `<svc>.<ns>.svc.cluster.local`; **headless** returns pod IPs.
- Pods point at CoreDNS via `/etc/resolv.conf` with a `search` list + `ndots:5`.
- Debug with `nslookup`/`dig` from a pod; check Endpoints when a name fails.

## Checklist
- [ ] Found CoreDNS pods, the `kube-dns` Service, and the `coredns` ConfigMap
- [ ] Read a pod's `/etc/resolv.conf` and explained `search` + `ndots`
- [ ] Resolved a Service by short and FQDN name from inside a pod
- [ ] Explained headless Service DNS (pod IPs) vs ClusterIP
- [ ] Know to allow port 53 egress when writing NetworkPolicies
