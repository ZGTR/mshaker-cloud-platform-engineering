# Examples

Runnable, self-contained hands-on examples that apply the concepts from the
`docs/` study notes to a real (local or cloud) Kubernetes cluster.

## Index
| Example | What it shows | Concepts (days) |
|---|---|---|
| [agent-state-service](./agent-state-service) | Multi-tenant FastAPI service that owns agents and their state; LoadBalancer + HPA autoscaling; IaC for AWS (EKS) & GCP (GKE) | Deployment, Service, LoadBalancer, requests/limits, HPA, probes (Day 7–18) |

## Conventions
- One folder per example, kebab-case (e.g. `agent-state-service`).
- Each example is **self-contained** and includes:
  - `README.md` — prerequisites, build, deploy, verify, cleanup
  - `app/` — application source + `Dockerfile`
  - `k8s/` — manifests, one resource per file
  - optional `iac/`, `load/`, `scripts/` as needed
- Use a **dedicated namespace** per example to keep the cluster tidy.
- Prefer `kind` for local clusters; provide `iac/` for cloud.

## Adding a new example
```
   examples/
     <new-example>/
       README.md
       app/
       k8s/
```
Copy the shape of `agent-state-service` and update the index table above.
