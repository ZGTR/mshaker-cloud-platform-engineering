# Plan — agent-state-service on Kubernetes (LoadBalancer + Autoscaling, multi-cloud IaC)

> A multi-tenant service that **owns agents and their state** (up / down /
> heartbeat) per tenant. Deployed on Kubernetes, exposed via a cloud
> **LoadBalancer**, **autoscaled** by an HPA, and provisioned with **IaC** on
> both AWS (EKS) and GCP (GKE).

## What it is
```
   Each tenant has many agents. The service is the source of truth for
   "is agent X up or down?" and accepts heartbeats.

   tenant "acme"            tenant "globex"
   ├── agent a1  [up]       ├── agent b1  [up]
   ├── agent a2  [down]     └── agent b2  [unknown]
   └── agent a3  [up]
```

## Request → state model
```
   client/agent ──► POST /tenants/{tenant}/agents/{id}/up
                    POST .../down
                    POST .../heartbeat
                    PUT  .../{id}   {"status":"up"}
                                │
                                ▼
                    ┌────────────────────────────┐
                    │  state store (per tenant)   │
                    │  (tenant, agent) -> status  │
                    │                  last_seen  │
                    └────────────────────────────┘
                                │
   dashboards ◄── GET /tenants/{tenant}/agents
                  GET /stats   (counts up/down/unknown)
```

## API surface
```
   GET    /                                   service info + which pod answered
   GET    /healthz   /readyz                  liveness / readiness probes
   GET    /stats                              tenant + agent counts by status
   GET    /tenants/{t}/agents                 list a tenant's agents
   GET    /tenants/{t}/agents/{id}            one agent (404 if missing)
   PUT    /tenants/{t}/agents/{id}            upsert {"status": "up|down|unknown"}
   POST   /tenants/{t}/agents/{id}/up         mark up
   POST   /tenants/{t}/agents/{id}/down       mark down
   POST   /tenants/{t}/agents/{id}/heartbeat  heartbeat (sets up)
   DELETE /tenants/{t}/agents/{id}            remove (204)
   GET    /load?ms=200                        synthetic CPU load to exercise HPA
```

## Runtime architecture
```
   external clients
        │
        ▼  (cloud LoadBalancer: AWS NLB / GCP Network LB)
   ╔══════════════════════════════════════╗
   ║ Service agent-state-lb (LoadBalancer) ║
   ╚════════════════════╤═════════════════╝
                        │ port 80 -> targetPort 8080
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ pod      │   │ pod      │   │ pod      │   Deployment agent-state
   │ :8080    │   │ :8080    │   │ :8080    │   (1..10 replicas)
   └──────────┘   └──────────┘   └──────────┘
        ▲ CPU%          ▲              ▲
        └───────────────┴──────────────┘
                        │
                 ┌──────────────┐      ┌────────────────┐
                 │     HPA       │◄─────│ metrics-server │
                 │ target 50%CPU │      └────────────────┘
                 └──────────────┘
```

## Why each piece
```
   Deployment      -> declarative pods, rolling updates, self-healing
   requests(cpu)   -> HPA computes utilization as usage / request
   Service(ClusterIP) -> stable in-cluster name: agent-state.agents:80
   Service(LB)     -> real external L4 LB (NLB on AWS, Network LB on GCP)
   HPA             -> add/remove replicas from observed CPU
   metrics-server  -> feeds CPU metrics to the HPA (built into GKE; Helm on EKS)
```

## Port mapping (concrete)
```
   internet ─► <LB-address>:80 ─► Service :80 ─► pod 10.244.0.x:8080
                                  (targetPort = containerPort 8080)
```

## Autoscaling behavior (verified locally)
```
   t=0    idle           cpu  ~4% / 50%   ─► 1 replica
   load on (6 clients)   cpu  >50%        ─► 1→3→5→7→9→10  (scaleUp +2 / 15s)
   peak                  cpu  51% / 50%   ─► 10 replicas (max)
   load off              cpu drops        ─► 10→9→8→...→1 (scaleDown after 60s)
```

## Multi-tenant state caveat (important)
```
   in-memory store lives INSIDE the pod process.

   replicas = 1                      replicas = N (after scale-out)
   ───────────                       ─────────────────────────────
   coherent reads/writes             LB spreads requests across pods
                                     → each pod has a DIFFERENT view
                                     → reads become inconsistent
```
The Dockerfile pins **1 Uvicorn worker** so state is coherent within a pod.
To scale the *stateful* reads horizontally, externalize state to a shared store:
```
   pods ──► ┌─────────────────────┐
            │ Redis / Postgres    │  single source of truth
            └─────────────────────┘
```
(`/load` is stateless, so autoscaling behavior is unaffected.)

## Health-probe lesson (why probes are lenient)
```
   single Python worker + CPU-bound /load holds the GIL
        └─► /healthz briefly slow to answer
            └─► aggressive liveness probe times out
                └─► kubelet RESTARTS the pod  (bad: load never sustains)

   fix: liveness timeoutSeconds:5, failureThreshold:6, periodSeconds:20
        → pod survives bursts, HPA scales instead of crash-looping
```

## Repo structure
```
   examples/
     README.md
     agent-state-service/
       README.md
       app/    main.py  requirements.txt  Dockerfile
       k8s/    namespace  deployment  service(ClusterIP)  service-lb(LoadBalancer)  hpa
       iac/    README.md  aws/(EKS .tf)  gcp/(GKE .tf)
       load/   load-test.sh
```

## Local run (kind) — the path that was verified
```
   kind create cluster --name agent-state
   apply metrics-server (+ --kubelet-insecure-tls)
   docker build -t agent-state-service:1.0.0 ./app
   kind load docker-image agent-state-service:1.0.0 --name agent-state
   kubectl apply -f k8s/{namespace,deployment,service,hpa}.yaml   # skip LB locally
   port-forward + curl the API
   ./load/load-test.sh ... + watch HPA scale up and back down
```

## Cloud run (IaC)
```
   AWS:  cd iac/aws && terraform apply           ─► EKS + nodes + metrics-server(Helm)
   GCP:  cd iac/gcp && terraform apply           ─► GKE + nodes (metrics-server built in)
   push image to ECR / Artifact Registry, set it in k8s/deployment.yaml
   kubectl apply -f k8s/   (incl. service-lb.yaml) ─► cloud LB external address
```

## Success criteria
- [x] API: tenants/agents up/down/heartbeat/list/stats/delete work
- [x] State coherent within a pod (1 worker)
- [x] HPA scales up under load and back down when idle (no crash-loops)
- [x] Manifests include a cloud LoadBalancer Service
- [x] IaC provisions a cluster on AWS (EKS) and GCP (GKE)

## Future work
- Externalize state to Redis/Postgres so reads are correct at N replicas.
- Ingress + TLS in front of the service; authn/authz per tenant.
- Push images via CI to ECR/Artifact Registry; GitOps (Argo/Flux) deploys.
