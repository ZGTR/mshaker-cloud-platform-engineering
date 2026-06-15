# NGINX Explained (in the Kubernetes context)

> Topic note: what NGINX is, why it shows up everywhere in k8s, with/without
> examples, and how it maps onto Pods, Services, and Ingress.

## What is NGINX?
NGINX (pronounced "engine-x") is a **web server** + **reverse proxy** +
**load balancer**. Two very different jobs use the same software:

```
   1) Web server        -> serves static files (HTML/CSS/JS/images)
   2) Reverse proxy     -> sits in front of backend apps, forwards requests
   3) Load balancer     -> spreads traffic across many backends
   4) TLS terminator    -> handles HTTPS so apps don't have to
```

In Kubernetes you meet NGINX in **two roles** — don't confuse them:

```
   (A) NGINX as YOUR app          (B) NGINX as the Ingress Controller
   ─────────────────────          ────────────────────────────────────
   a plain web server you         a cluster-wide router that sends
   deploy in a Pod (e.g. to       external traffic to the right Service
   serve a site or as a proxy)    based on host/path rules
```

## Forward proxy vs Reverse proxy (the core idea)
```
   FORWARD PROXY (protects/represents the CLIENT)
   client ──► [forward proxy] ──► internet ──► server
              (hides who the client is)

   REVERSE PROXY = NGINX (protects/represents the SERVER)
   client ──► internet ──► [NGINX reverse proxy] ──► backend app(s)
                           (hides how many servers,
                            does TLS, caching, LB)
```

## WITHOUT NGINX vs WITH NGINX

### Plain servers, no proxy
```
   WITHOUT NGINX                          WITH NGINX (reverse proxy)
   ─────────────                          ──────────────────────────

   client ──► app:3000   (Node.js)        client ──► ╔═══════════╗ ──► app:3000
   client ──► api:5000   (Python)                    ║   NGINX   ║ ──► api:5000
   client ──► static files?? (none)       client ──► ║  :80/:443 ║ ──► static/
                                                     ╚═══════════╝
   Problems:                              One stable entry point:
   - client must know every port          - one host/port (80/443)
   - no HTTPS unless each app does it      - TLS terminated once
   - no single place for caching/LB        - routing by path/host
   - each app exposed directly             - apps stay private
```

### Concrete example: routing by path
```
   https://shop.example.com/          ──► NGINX ──► frontend  :3000
   https://shop.example.com/api/...   ──► NGINX ──► backend   :5000
   https://shop.example.com/static/.. ──► NGINX ──► static files on disk
```

Minimal `nginx.conf` for that:
```nginx
server {
    listen 80;
    server_name shop.example.com;

    location /api/ {
        proxy_pass http://backend:5000/;   # forward to backend service
    }

    location /static/ {
        root /usr/share/nginx/html;        # serve files directly
    }

    location / {
        proxy_pass http://frontend:3000/;  # everything else -> frontend
    }
}
```

## Load balancing example
```
   WITHOUT (one backend)                  WITH (NGINX upstream pool)
   ─────────────────────                  ──────────────────────────
                                                       ┌─► app-1:3000
   client ──► app:3000                    client ──► NGINX ─► app-2:3000
   (single point, no spread)                          └─► app-3:3000
                                          (round-robin / least-conn)
```
```nginx
upstream app_pool {
    server app-1:3000;
    server app-2:3000;
    server app-3:3000;
}
server {
    listen 80;
    location / { proxy_pass http://app_pool; }
}
```

## NGINX in Kubernetes

### Role A — NGINX as a Pod (your web server / proxy)
```
   ┌──────────── Node ────────────┐
   │  ┌──────── Pod ────────┐      │
   │  │  nginx container     │      │
   │  │  :80  serves site    │◄──── Service "web" (ClusterIP) ◄── other pods
   │  └──────────────────────┘      │
   └───────────────────────────────┘
```
```bash
kubectl create deployment web --image=nginx
kubectl expose deployment web --port=80
```

### Role B — NGINX Ingress Controller (cluster router)
A Service only gives ONE entry per app. **Ingress** lets one external IP route
to many Services by host/path — and the NGINX Ingress Controller is the Pod that
actually does the routing.

```
   WITHOUT Ingress                         WITH NGINX Ingress
   ───────────────                         ───────────────────
   each app needs its own                  one LoadBalancer ──► NGINX Ingress
   LoadBalancer (costly):                  Controller routes by rule:

   LB1 ──► svc-shop                         internet
   LB2 ──► svc-blog                            │
   LB3 ──► svc-api                             ▼
                                          ╔═══════════════════════╗
   (3 cloud LBs = 3x cost)                ║ NGINX Ingress (1 LB)  ║
                                          ╚══════════╤════════════╝
                                       shop.ex.com ──┼──► svc-shop ─► pods
                                       blog.ex.com ──┼──► svc-blog ─► pods
                                       /api  path  ──┴──► svc-api  ─► pods
```

Ingress resource (the rules the controller reads):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: svc-api
                port:
                  number: 5000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: svc-shop
                port:
                  number: 3000
```

## How the pieces connect
```
   internet
       │
       ▼  (cloud LoadBalancer, 1 public IP)
   ╔══════════════════════════╗
   ║ NGINX Ingress Controller ║   reads Ingress rules
   ╚════════════╤═════════════╝
                │ host/path match
        ┌───────┼────────┐
        ▼       ▼        ▼
     svc-shop svc-blog svc-api      (ClusterIP Services)
        │       │        │
        ▼       ▼        ▼
     [pods]  [pods]   [pods]
```

## Key takeaways
- NGINX = **web server + reverse proxy + load balancer + TLS terminator**.
- A **reverse proxy** represents the *server side* (one entry, hides backends).
- In k8s NGINX shows up as **(A) a plain app Pod** OR **(B) the Ingress
  Controller** — same software, different job.
- **Service** = one stable entry per app. **Ingress (NGINX)** = one entry for
  *many* apps, routed by host/path, saving cloud LB cost.

## Checklist
- [ ] Ran `nginx` in a Pod and reached it via a Service
- [ ] Wrote an `nginx.conf` with `proxy_pass` and a `location` block
- [ ] Installed the NGINX Ingress Controller
- [ ] Routed two hosts/paths to two Services through one Ingress
- [ ] Can explain reverse proxy vs forward proxy
