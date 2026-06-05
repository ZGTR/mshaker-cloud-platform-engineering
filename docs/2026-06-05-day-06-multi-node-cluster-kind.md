# Day 6 — Multi-Node Cluster Setup with Kind

> Video: Day 6/40 — Kubernetes Multi Node Cluster Setup Step By Step | Kind
> https://www.youtube.com/watch?v=RORhczcOrWs
> Duration: ~27 min

## What is Kind?
**Kind = Kubernetes IN Docker.** It runs each Kubernetes "node" as a Docker
container. Perfect for local learning/CI — a full multi-node cluster on a laptop.

```
   Your laptop
   +--------------------------------------------------+
   |  Docker Engine                                    |
   |  +------------+  +------------+  +------------+    |
   |  | container  |  | container  |  | container  |   |
   |  | = control  |  | = worker 1 |  | = worker 2 |   |
   |  |   plane    |  |            |  |            |   |
   |  +------------+  +------------+  +------------+    |
   |        \_______ one Kind cluster ________/        |
   +--------------------------------------------------+
```

## Install (macOS/Linux)
```bash
# kind
brew install kind          # or: go install / curl binary
# kubectl
brew install kubectl
docker --version           # Docker must be running
```

## Create a cluster config (multi-node)
`kind-config.yaml`:
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

## Spin it up
```bash
kind create cluster --name cka --config kind-config.yaml

# kind auto-configures kubectl context to this cluster
kubectl cluster-info --context kind-cka
kubectl get nodes
```

Expected:
```
NAME                 STATUS   ROLES           AGE   VERSION
cka-control-plane    Ready    control-plane   1m    v1.xx
cka-worker           Ready    <none>          1m    v1.xx
cka-worker2          Ready    <none>          1m    v1.xx
```

## kubectl context (which cluster am I talking to?)
```bash
kubectl config get-contexts
kubectl config current-context
kubectl config use-context kind-cka
```

```
   kubectl  --(context)-->  which API server + creds to use
            kubeconfig file (~/.kube/config) holds them
```

## Useful kind ops
```bash
kind get clusters            # list clusters
kind delete cluster --name cka
docker ps                    # see the node containers
```

## Pin a Kubernetes version (handy for CKA practice)
```bash
kind create cluster --name cka \
  --image kindest/node:v1.30.0 --config kind-config.yaml
```

## Key takeaways
- Kind nodes are **Docker containers**, not VMs — fast and disposable.
- One config file defines control-plane + worker roles.
- `kubectl` talks to the cluster via the **context** in your kubeconfig.

## Checklist
- [ ] Installed kind + kubectl, Docker running
- [ ] Created a 3-node cluster from config
- [ ] `kubectl get nodes` shows control-plane + 2 workers Ready
- [ ] Switched contexts and deleted a cluster
