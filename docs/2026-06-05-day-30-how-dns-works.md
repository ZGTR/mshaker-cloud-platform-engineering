# Day 30 — How DNS Works

> Video: Day 30/40 — How does DNS work?
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Problem & solution
Computers talk over IP addresses, but humans remember names. DNS is the
distributed phone book that turns `www.example.com` into an IP. You can't debug
Kubernetes networking (Day 31+) until you understand the plain-internet DNS flow
first: who answers, what gets cached, and which files decide the result.

**Solution:** Resolve names by walking the stub then recursive resolver then root/TLD/authoritative chain, caching at each hop for the record's TTL.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | +----------------------------------------------------------------+ |
   | +------- WORKER NODE   (kubelet | kube-proxy | runtime) --------+  |
   | | +------------------- namespace: default --------------------+ |  |
   | | | +----- POD -----+                                         | |  |
   | | | | + CONTAINER + |                                         | |  |
   | | | | | app       | |                                         | |  |
   | | | | +-----------+ |                                         | |  |
   | | | +---------------+                                         | |  |
   | | |    <== CoreDNS (in kube-system) answers DNS for every pod | |  |
   | | +-----------------------------------------------------------+ |  |
   | +---------------------------------------------------------------+  |
   +--------------------------------------------------------------------+
```

## The resolution chain
A name is resolved by walking a hierarchy: your **stub resolver** asks a
**recursive resolver**, which (if nothing is cached) walks the **root -> TLD ->
authoritative** servers.

```
   stub resolver (your OS)  ->  recursive resolver (ISP / 8.8.8.8 / 1.1.1.1)
        |                              |
        |                              +-- root server     ".":      "ask .com"
        |                              +-- TLD server      ".com":   "ask example's NS"
        |                              +-- authoritative   example.com: "A = 93.184.216.34"
        v
   answer cached at every hop for the record's TTL
```

## End-to-end: typing a URL
```
   +---------+        +----------+        +---------------+
   | browser |        | resolver |        | authoritative |
   +---------+        +----------+        +---------------+
        |                   |                     |
        | (1) A? www.example.com                  |
        |------------------>|                     |
        |                   |                     |
     (2) resolver checks cache; if cold, walks root -> TLD -> authoritative
        |                   |                     |
        |                   | (3) who is www.example.com?
        |                   |-------------------->|
        |                   |                     |
        |                   | (4) A 93.184.216.34 (TTL 300)
        |                   |<--------------------|
        |                   |                     |
        | (5) 93.184.216.34 (cached for the TTL)  |
        |<------------------|                     |
        |                   |                     |
   The browser then opens TCP/443 to that IP. /etc/hosts wins before DNS.
```

## Record types you must know
```
   A      name -> IPv4              www.example.com -> 93.184.216.34
   AAAA   name -> IPv6              www.example.com -> 2606:2800:220:1:...
   CNAME  alias -> another name     shop.example.com -> www.example.com
   NS     which servers are authoritative for a zone
   MX     mail servers for a domain
   TXT    free text (SPF, domain verification, ACME challenges)
   PTR    IP -> name (reverse DNS)
   SRV    service location (host + port) — used heavily inside Kubernetes
```

## Files & tools on a Linux host
The order the OS resolves a name is configurable, and `/etc/hosts` is checked
before DNS for most setups.

```bash
cat /etc/hosts          # static name -> IP overrides (checked first)
cat /etc/resolv.conf    # which resolver(s) to ask + search domains + ndots
cat /etc/nsswitch.conf  # the "hosts:" line sets files-vs-dns order

dig www.example.com            # full query + answer + TTL
dig +short www.example.com     # just the IP
dig +trace www.example.com     # walk root -> TLD -> authoritative yourself
nslookup www.example.com       # simpler lookup
getent hosts www.example.com   # resolve the way the OS (nsswitch) would
```

## TTL & caching (why changes are "slow")
Every record carries a **TTL**. Resolvers cache answers for that long, so a DNS
change can take up to the old TTL to propagate. Lower the TTL *before* a planned
migration, then raise it again afterwards.

```
   record TTL = 300s  ->  resolvers may serve the OLD IP for up to 5 minutes
   plan a cutover: drop TTL to 60s a day early, migrate, then restore
```

## Key takeaways
- DNS resolves names by walking **root -> TLD -> authoritative**, caching at each hop.
- The **recursive resolver** does the walking; your OS stub just asks it.
- `/etc/hosts` (via `nsswitch`) usually wins **before** DNS is even queried.
- Records: **A/AAAA** (IP), **CNAME** (alias), **NS/MX/TXT/PTR/SRV**.
- **TTL** controls caching — lower it before planned cutovers.
- `dig +trace` and `getent hosts` are your debugging workhorses.

## Checklist
- [ ] Can describe the stub -> recursive -> root/TLD/authoritative chain
- [ ] Read `/etc/resolv.conf` and `/etc/hosts` on a host
- [ ] Used `dig +short` and `dig +trace` on a real domain
- [ ] Can explain TTL and why DNS changes appear delayed
- [ ] Know A vs CNAME vs SRV (SRV matters for Day 31)
