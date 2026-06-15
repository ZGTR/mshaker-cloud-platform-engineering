# IaC — Provision a cluster for agent-state-service

Terraform to stand up a managed Kubernetes cluster on **AWS (EKS)** or
**GCP (GKE)**. After the cluster exists, deploy the service with the manifests in
`../k8s/` (including the `LoadBalancer` Service for external access).

```
   terraform apply ─► cluster + nodes ─► kubectl apply -f ../k8s/ ─► Cloud LB ─► pods
```

| Cloud | Dir | LB created by `service-lb.yaml` | metrics-server |
|---|---|---|---|
| AWS | `aws/` (EKS) | Network Load Balancer (NLB) | installed by Terraform (Helm) |
| GCP | `gcp/` (GKE) | Network Load Balancer | built into GKE |

## AWS (EKS)
Prereqs: `terraform`, `awscli` (logged in), `kubectl`, `helm`.
```bash
cd aws
terraform init
terraform apply -var="region=us-east-1"
$(terraform output -raw configure_kubectl)   # update kubeconfig
```

## GCP (GKE)
Prereqs: `terraform`, `gcloud` (logged in), `kubectl`. APIs: container, compute.
```bash
cd gcp
terraform init
terraform apply -var="project_id=YOUR_PROJECT" -var="region=us-central1"
$(terraform output -raw configure_kubectl)   # update kubeconfig
```

## Push the image (cloud nodes can't see local Docker)
- AWS: push to **ECR**, set the image in `../k8s/deployment.yaml`.
- GCP: push to **Artifact Registry**, set the image in `../k8s/deployment.yaml`.

## Deploy + get the external address
```bash
kubectl apply -f ../k8s/
kubectl -n agents get svc agent-state-lb -w   # wait for EXTERNAL-IP / hostname
```

## Teardown (avoid charges)
```bash
kubectl delete -f ../k8s/      # delete the LB Service first so the cloud LB is released
terraform destroy
```
