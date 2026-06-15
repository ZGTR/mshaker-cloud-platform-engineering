# agent-state-service

A multi-tenant service that **owns agents and their state** (up / down /
heartbeat) per tenant. Built with FastAPI, deployed on Kubernetes, exposed
through a cloud **LoadBalancer**, and **autoscaled** by an HPA under load.
Cluster provisioning is **IaC** for both AWS (EKS) and GCP (GKE).

```
   tenant clients ──► Cloud LB ──► Service ──┬─► [agent-state pod]  (1..10)
                                             ├─► [agent-state pod]
                                             └─► [agent-state pod]
                          ▲                        │ CPU%
                          └──── HPA ◄── metrics-server ─┘
```

## API
| Method | Route | Purpose |
|---|---|---|
| GET | `/` | service info + pod that served you |
| GET | `/healthz` / `/readyz` | liveness / readiness probes |
| GET | `/stats` | tenant + agent counts, breakdown by status |
| GET | `/tenants/{tenant}/agents` | list a tenant's agents + states |
| GET | `/tenants/{tenant}/agents/{id}` | get one agent |
| PUT | `/tenants/{tenant}/agents/{id}` | upsert agent (body: `{"status":"up"}`) |
| POST | `/tenants/{tenant}/agents/{id}/up` | mark agent up |
| POST | `/tenants/{tenant}/agents/{id}/down` | mark agent down |
| POST | `/tenants/{tenant}/agents/{id}/heartbeat` | heartbeat (sets up) |
| DELETE | `/tenants/{tenant}/agents/{id}` | remove agent |
| GET | `/load?ms=300` | synthetic CPU load to exercise the HPA |

> State note: the store is **in-memory per pod**. With multiple replicas it is
> NOT shared — fine to learn the mechanics, but production must externalize
> state to Redis/Postgres (see the plan doc).

## Layout
```
   app/    main.py, requirements.txt, Dockerfile   (the service)
   k8s/    namespace, deployment, service (ClusterIP), service-lb (LoadBalancer), hpa
   iac/    aws/ (EKS) and gcp/ (GKE) Terraform + iac/README.md
   load/   load-test.sh (drive CPU to trigger autoscaling)
```

## Run locally (kind)
```bash
kind create cluster --name agent-state

# metrics-server (HPA needs it); kind: allow insecure kubelet TLS
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment metrics-server

# build + load image into kind
docker build -t agent-state-service:1.0.0 ./app
kind load docker-image agent-state-service:1.0.0 --name agent-state

# deploy (skip service-lb.yaml locally; kind has no cloud LB)
kubectl apply -f k8s/namespace.yaml -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/hpa.yaml
kubectl -n agents rollout status deployment/agent-state
```

## Try it
```bash
kubectl -n agents port-forward svc/agent-state 8080:80 &
curl -s localhost:8080/ | jq
curl -s -X POST localhost:8080/tenants/acme/agents/a1/up | jq
curl -s -X POST localhost:8080/tenants/acme/agents/a2/down | jq
curl -s localhost:8080/tenants/acme/agents | jq
curl -s localhost:8080/stats | jq
```

## Watch it autoscale
```bash
kubectl -n agents get hpa -w
kubectl -n agents get pods -w
```
```bash
chmod +x load/load-test.sh
./load/load-test.sh "http://localhost:8080/load?ms=300" 20 120
```
```
   idle:        CPU ~  5%  -> 1 replica
   under load:  CPU > 50%  -> HPA scales 1 -> 3 -> ... up to 10
   load stops:  CPU drops  -> back to 1 (after ~60s window)
```

## Run on a cloud (AWS / GCP)
See [`iac/README.md`](./iac/README.md): `terraform apply`, push the image to
ECR/Artifact Registry, `kubectl apply -f k8s/` (incl. `service-lb.yaml`), then
hit the LoadBalancer's external address.

## Cleanup
```bash
kubectl delete -f k8s/      # delete LB Service first to release the cloud LB
kind delete cluster --name agent-state   # local only
```
