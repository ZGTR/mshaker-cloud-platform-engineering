# Day 33 — Ingress Controllers and Ingress Resources

> Video: Day 33/40 — Ingress controller and Ingress resources
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| Ingress resource | HTTP routing rules (host/path) |
| Ingress controller | The proxy that fulfills them (e.g. nginx) |
| Host/path routing | Send traffic based on the URL |
| pathType | Exact / Prefix matching |
| TLS termination | HTTPS handled at the ingress |
| Backend | The Service an ingress routes to |

## Problem & solution
Exposing every Service as its own `LoadBalancer` is expensive (one cloud LB
each) and gives you no shared routing, TLS, or host/path rules. **Ingress** lets
one entry point route external HTTP(S) traffic to many Services by **hostname and
path**, with TLS termination — using a single load balancer.

**Solution:** Install an ingress controller and define Ingress rules to route external HTTP(S) by host/path to many Services through one load balancer, terminating TLS.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------- CLUSTER --------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | +----------------------------------------------------------------+     |
   | +---------- WORKER NODE   (kubelet | kube-proxy | runtime) ----------+ |
   | | +---------------------- namespace: default ----------------------+ | |
   | | | +----------------------- POD -----------------------+          | | |
   | | | | + CONTAINER +                                     |          | | |
   | | | | | app       |                                     |          | | |
   | | | | +-----------+                                     |          | | |
   | | | |    <== the ingress controller itself runs as pods |          | | |
   | | | +---------------------------------------------------+          | | |
   | | |    <== Ingress + controller route external HTTP(S) to Services | | |
   | | +----------------------------------------------------------------+ | |
   | +--------------------------------------------------------------------+ |
   +------------------------------------------------------------------------+
```

## Two pieces: resource vs controller
```
   Ingress RESOURCE    = the rules (host/path -> Service). Just YAML; does nothing alone.
   Ingress CONTROLLER  = the pods that READ those rules and actually route traffic
                         (nginx, Traefik, HAProxy, or a cloud controller).
```
> An Ingress resource with **no controller installed** does nothing. You must
> install a controller first.

## Install a controller (ingress-nginx example)
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.0/deploy/static/provider/cloud/deploy.yaml
kubectl -n ingress-nginx get pods,svc      # the controller + its LoadBalancer Service
```
The controller's own Service (type `LoadBalancer` or `NodePort`) is the single
public entry point; everything else routes through it.

## An Ingress resource
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
    - hosts: ["shop.example.com"]
      secretName: shop-tls           # a TLS Secret (cert + key)
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /cart
            pathType: Prefix
            backend:
              service:
                name: cart
                port: { number: 80 }
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port: { number: 8080 }
```

## End-to-end: a request through Ingress
```
   +--------+        +---------+        +---------+        +-----+
   | client |        | ingress |        | service |        | pod |
   +--------+        +---------+        +---------+        +-----+
        |                 |                  |                |
        | (1) GET https://shop.example.com/cart               |
        |---------------->|                  |                |
        |                 |                  |                |
     (2) controller matches host + path -> a backend Service; TLS terminates here
        |                 |                  |                |
        |                 | (3) forward to the Service (ClusterIP)
        |                 |----------------->|                |
        |                 |                  |                |
        |                 |                  | (4) kube-proxy load-balances to a ready pod
        |                 |                  |--------------->|
        |                 |                  |                |
        | (5) 200 OK      |                  |                |
        |<----------------------------------------------------|
        |                 |                  |                |
   One LB + one ingress controller fans out to many Services by host/path.
```

## pathType & routing rules
```
   pathType: Prefix   /api matches /api, /api/v1, /api/x   (most common)
   pathType: Exact    /api matches ONLY /api
   host-based         shop.example.com vs admin.example.com -> different Services
   default backend    requests matching no rule -> a fallback Service (e.g. 404 page)
```

## TLS termination
Put the cert + key in a `kubernetes.io/tls` Secret and reference it in
`spec.tls`. The controller terminates HTTPS and forwards plain HTTP to the
Service (see Day 20 for re-encrypt/passthrough options).

```bash
kubectl create secret tls shop-tls --cert=shop.crt --key=shop.key
```

## Common pitfalls
```
   - Ingress created but 404/no route   -> no controller installed, or wrong ingressClassName
   - TLS not working                    -> Secret missing/wrong type, or host mismatch
   - paths leak to wrong app            -> rewrite-target / pathType misconfigured
   - works in-cluster, not externally   -> the controller Service has no external IP
   - cert-manager for real certs        -> automate Let's Encrypt instead of manual Secrets
```

## Key takeaways
- **Ingress resource** = routing rules; **Ingress controller** = the pods that enforce them.
- A resource without a controller does **nothing** — install one first.
- Route by **host + path**; terminate **TLS** with a tls Secret; one LB for many apps.
- `ingressClassName` ties a resource to a specific controller.
- Use **cert-manager** to automate certificates in production.

## Checklist
- [ ] Explained resource vs controller and why both are needed
- [ ] Installed an ingress controller and found its external Service
- [ ] Wrote an Ingress with host + multiple path rules
- [ ] Added TLS via a tls Secret and tested HTTPS
- [ ] Diagnosed a 404 (missing controller / wrong ingressClassName)
