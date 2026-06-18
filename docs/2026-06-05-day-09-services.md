# Day 9 — Kubernetes Services: ClusterIP vs NodePort vs LoadBalancer vs ExternalName

> Video: Day 9/40 — Kubernetes Services Explained
> https://www.youtube.com/watch?v=tHAQWLKMTB0
> Duration: ~46 min

## Problem & solution
Pods are ephemeral and get a new IP each time they are recreated, so nothing
can reliably address them. We need a stable virtual IP and DNS name that
load-balances across a constantly changing set of matching pods.

**Solution:** Put a Service (ClusterIP/NodePort/LoadBalancer) in front of pods for a stable IP/DNS that load-balances to healthy pods.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | +----------------------------------------------------------------+ |
   | +------ WORKER NODE   (kubelet | kube-proxy | runtime) -------+    |
   | | +------------------ namespace: default -------------------+ |    |
   | | | +------------------- POD -------------------+           | |    |
   | | | | + CONTAINER +                             |           | |    |
   | | | | | app       |                             |           | |    |
   | | | | +-----------+                             |           | |    |
   | | | |    <== selected by the Service via labels |           | |    |
   | | | +-------------------------------------------+           | |    |
   | | |    <== a Service gives a stable IP/DNS in front of pods | |    |
   | | +---------------------------------------------------------+ |    |
   | +-------------------------------------------------------------+    |
   +--------------------------------------------------------------------+
```

## Why Services exist
Pods are **ephemeral** — they die and get recreated with **new IPs**. You can't
rely on a pod IP. A **Service** gives a **stable virtual IP + DNS name** and
load-balances across the matching pods.

Pods run **on nodes**. Each pod gets its own IP; the container listens on a
**containerPort** (e.g. `8080`). Nodes have their own IPs too.

```
   WITHOUT Service                              WITH Service
   ──────────────                               ────────────

   ┌──── Node A (192.168.0.11) ────┐            ┌──── Node A (192.168.0.11) ────┐
   │  [pod 10.1.1.5 :8080]  ✗      │            │  [pod 10.1.1.7 :8080]         │
   └───────────────────────────────┘            └─────────────▲─────────────────┘
              ▲                                                │
              │  client hits pod IP                 ╔══════════╪══════════╗
              │  directly                           ║ Service "web"       ║
   client ────┘                          client ──► ║ ClusterIP 10.96.0.5 ║
                                                    ║   port 80           ║
   pod dies → new IP 10.1.1.9 →                     ╚══════════╪══════════╝
   client still points at .5 → BREAKS              targetPort 8080
                                                                │
                                              ┌─────────────────┴────────────────┐
                                   ┌──── Node A ────┐          ┌──── Node B (192.168.0.12) ────┐
                                   │ [pod 10.1.1.7  │          │ [pod 10.1.1.8 :8080]          │
                                   │      :8080]    │          │ [pod 10.1.1.9 :8080]          │
                                   └────────────────┘          └───────────────────────────────┘
                                   (stable IP/DNS + load-balanced across pods on any node)
```

## How a Service finds its pods: labels & selectors
A Service has no hard-coded pod list — its **selector** matches pod **labels**,
and the matching pod IPs become the Service's **Endpoints**.

```
   ┌──────────────────────────────┐
   │ Service                       │
   │   spec.selector: app=web      │
   └──────────────┬───────────────┘
                  │ matches label app=web
        ┌─────────┼─────────┐
        ▼         ▼         ▼
   ┌─────────┐┌─────────┐┌─────────┐
   │ pod     ││ pod     ││ pod     │
   │ app=web ││ app=web ││ app=web │
   └─────────┘└─────────┘└─────────┘
        │         │         │
        └─────────┴─────────┘
                  ▼
        Endpoints = [podIP, podIP, podIP]
```

```bash
kubectl get endpoints <svc>     # the actual pod IPs behind a service
```

## The 4 Service types

### 1) ClusterIP (default) — internal only
Gives a stable virtual IP reachable **only inside** the cluster.

```
   ┌───────────────────────── cluster ─────────────────────────┐
   │                                                            │
   │  [client pod] ──► ╔════════════╗ ──┬─► [pod]               │
   │                   ║ ClusterIP  ║   └─► [pod]               │
   │                   ╚════════════╝                           │
   │                                                            │
   │   ✗ NOT reachable from outside the cluster                 │
   └────────────────────────────────────────────────────────────┘
```
Use for pod-to-pod / internal microservice traffic.

### 2) NodePort — expose on every node's IP at a high port
Opens the same high port on **every node**, forwarding outside traffic to the
pods.

```
              ┌──────────── cluster ────────────┐
   user ──►   │  Node A :30007 ┐                 │
   NodeIP     │                ├─► ╔══════════╗  │
   :30007 ──► │  Node B :30007 ┘   ║ NodePort ║─►├─► [pod][pod]
              │  (every node forwards the port,  │
              │   even nodes with no pod)        │
              └──────────────────────────────────┘
              port range: 30000–32767
```

### 3) LoadBalancer — cloud external LB
Asks the cloud provider for a **public IP** and front-ends the service with a
managed load balancer.

```
   internet ──► ╔══════════════╗ ──► NodePort ──► ClusterIP ──► [pods]
                ║  Cloud LB     ║
                ║  (public IP)  ║   provisioned by cloud provider
                ╚══════════════╝   (AWS / GCP / Azure)
```

### 4) ExternalName — DNS alias to an external host
Maps the service name to an external DNS host via a **CNAME** — no pods, no
proxying.

```
   [pod] ──► svc(my-db) ┄┄CNAME┄┄► db.example.com
            (no selector, no pods, no proxying — just a DNS record)
```

## Layering (each type builds on the previous)
Each type wraps the one below it: LoadBalancer sits on NodePort, which sits on
ClusterIP.

```
   ┌─────────────────────────────────────────┐
   │ LoadBalancer  (cloud public IP)          │
   │  ┌──────────────────────────────────┐    │
   │  │ NodePort  (NodeIP:30007)          │    │
   │  │  ┌────────────────────────────┐   │    │
   │  │  │ ClusterIP  (internal VIP)  │──►── Pods
   │  │  └────────────────────────────┘   │    │
   │  └──────────────────────────────────┘    │
   └─────────────────────────────────────────┘
```

## Service YAML examples
Minimal manifests for the two types you create most often.

ClusterIP:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
    - port: 80          # service port
      targetPort: 80    # container port
```

NodePort:
```yaml
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30007   # optional; auto-assigned if omitted
```

## port vs targetPort vs nodePort
These three ports map the hop from node, to service, to container — keep them
straight.

```
   user/internet
        │   curl 192.168.0.11:30007
        ▼  nodePort 30007    ── on each Node's IP (30000–32767)   [NodePort/LB only]
   ┌──────────────────────────┐
   │ Node  192.168.0.11        │
   └──────────────────────────┘
        │
        ▼  port 80            ── on the Service's ClusterIP 10.96.0.5
   ╔══════════════════════════╗
   ║ Service "web" 10.96.0.5   ║      in-cluster: curl web:80
   ╚══════════════════════════╝
        │
        ▼  targetPort 8080    ── on the Pod/container (= containerPort)
   ┌──────────────────────────┐
   │ Pod   10.1.1.8  :8080     │
   └──────────────────────────┘

   Example mapping:  192.168.0.11:30007  →  10.96.0.5:80  →  10.1.1.8:8080
                     (NodeIP:nodePort)      (svc:port)        (podIP:targetPort)
```

## Commands
Everyday commands to expose a Deployment, inspect the Service, and test it from
inside the cluster.

```bash
kubectl expose deployment web --port=80 --target-port=80 --type=NodePort
kubectl get svc
kubectl get svc web -o wide
kubectl describe svc web

# test internal DNS from another pod
kubectl run tmp --image=busybox -it --rm -- wget -qO- web:80
```

## Service DNS name
Every Service gets an in-cluster DNS name built from its name, namespace, and the
cluster domain.

```
   web   .   default   .   svc   .   cluster.local
   ───       ───────       ───       ─────────────
  service   namespace     type        cluster
   name                   marker      domain

   e.g.  web.default.svc.cluster.local
```

## Key takeaways
- Services give a **stable IP/DNS + load balancing** over ephemeral pods.
- **ClusterIP** internal, **NodePort** node IPs, **LoadBalancer** cloud public,
  **ExternalName** DNS alias.
- Remember the **port / targetPort / nodePort** trio.

## Checklist
- [ ] Exposed a Deployment as ClusterIP and reached it from another pod
- [ ] Created a NodePort and hit it on a node IP
- [ ] Inspected `kubectl get endpoints`
- [ ] Can explain port vs targetPort vs nodePort
