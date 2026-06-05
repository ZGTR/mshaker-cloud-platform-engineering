# CKA — 40 Days of Kubernetes (Study Notes)

Follow-along notes for **Certified Kubernetes Administrator (CKA)** based on the
playlist *"Certified Kubernetes Administrator Full Course For Beginners | CKA 2026"*
by [Tech Tutorials with Piyush](https://www.youtube.com/@TechTutorialswithPiyush).

Playlist: https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

Each doc has: goal, key concepts, ASCII diagrams, runnable commands, and a checklist.

## Index (Days 0–29)

| Day | Topic | Doc |
|-----|-------|-----|
| 0 | CKA Course Intro & Roadmap | [day-00](docs/2026-06-05-day-00-cka-roadmap.md) |
| 1 | Docker Fundamentals | [day-01](docs/2026-06-05-day-01-docker-fundamentals.md) |
| 2 | How To Dockerize a Project | [day-02](docs/2026-06-05-day-02-dockerize-a-project.md) |
| 3 | Multi-Stage Docker Build | [day-03](docs/2026-06-05-day-03-multi-stage-docker-build.md) |
| 4 | Why Kubernetes Is Used | [day-04](docs/2026-06-05-day-04-why-kubernetes.md) |
| 5 | Kubernetes Architecture | [day-05](docs/2026-06-05-day-05-kubernetes-architecture.md) |
| 6 | Multi-Node Cluster with Kind | [day-06](docs/2026-06-05-day-06-multi-node-cluster-kind.md) |
| 7 | Pods: Imperative vs Declarative | [day-07](docs/2026-06-05-day-07-pods-imperative-vs-declarative.md) |
| 8 | Deployment, RC & ReplicaSet | [day-08](docs/2026-06-05-day-08-deployment-rc-replicaset.md) |
| 9 | Services (ClusterIP/NodePort/LB) | [day-09](docs/2026-06-05-day-09-services.md) |
| 10 | Namespaces | [day-10](docs/2026-06-05-day-10-namespaces.md) |
| 11 | Multi-Container Pods (Sidecar/Init) | [day-11](docs/2026-06-05-day-11-multi-container-pod-sidecar-init.md) |
| 12 | DaemonSet, Job & CronJob | [day-12](docs/2026-06-05-day-12-daemonset-job-cronjob.md) |
| 13 | Static Pods, Manual Scheduling, Labels | [day-13](docs/2026-06-05-day-13-static-pods-manual-scheduling-labels.md) |
| 14 | Taints and Tolerations | [day-14](docs/2026-06-05-day-14-taints-and-tolerations.md) |
| 15 | Node Affinity | [day-15](docs/2026-06-05-day-15-node-affinity.md) |
| 16 | Requests and Limits | [day-16](docs/2026-06-05-day-16-requests-and-limits.md) |
| 17 | Autoscaling (HPA vs VPA) | [day-17](docs/2026-06-05-day-17-autoscaling-hpa-vpa.md) |
| 18 | Health Probes (Liveness/Readiness) | [day-18](docs/2026-06-05-day-18-health-probes.md) |
| 19 | ConfigMap and Secret | [day-19](docs/2026-06-05-day-19-configmap-and-secret.md) |
| 20 | SSL/TLS Explained | [day-20](docs/2026-06-05-day-20-ssl-tls-explained.md) |
| 21 | TLS in Kubernetes | [day-21](docs/2026-06-05-day-21-tls-in-kubernetes.md) |
| 22 | Authentication and Authorization | [day-22](docs/2026-06-05-day-22-authentication-and-authorization.md) |
| 23 | RBAC: Role and RoleBinding | [day-23](docs/2026-06-05-day-23-rbac-role-and-rolebinding.md) |
| 24 | ClusterRole and ClusterRoleBinding | [day-24](docs/2026-06-05-day-24-clusterrole-and-clusterrolebinding.md) |
| 25 | Service Accounts | [day-25](docs/2026-06-05-day-25-service-accounts.md) |
| 26 | Network Policies | [day-26](docs/2026-06-05-day-26-network-policies.md) |
| 27 | Multi-Node Cluster with kubeadm | [day-27](docs/2026-06-05-day-27-kubeadm-cluster-setup.md) |
| 28 | Docker Storage Fundamentals | [day-28](docs/2026-06-05-day-28-docker-storage-fundamentals.md) |
| 29 | Storage in Kubernetes (PV/PVC) | [day-29](docs/2026-06-05-day-29-kubernetes-storage-pv-pvc.md) |

## Cloud-Native Platform Engineering (CNPE)

Building on the CKA foundation: a full platform-engineering curriculum.
Start here → [CNPE Curriculum & Plan](docs/2026-06-05-cloud-native-platform-engineering-curriculum.md)

| # | Topic | Folder |
|---|-------|--------|
| 01 | Kubernetes Foundation | [cnpe/01-kubernetes](docs/cnpe/01-kubernetes/README.md) |
| 02 | GitOps / Argo CD | [cnpe/02-gitops-argocd](docs/cnpe/02-gitops-argocd/README.md) |
| 03 | Policy-as-Code / Kyverno | [cnpe/03-policy-as-code-kyverno](docs/cnpe/03-policy-as-code-kyverno/README.md) |
| 04 | Service Mesh | [cnpe/04-service-mesh](docs/cnpe/04-service-mesh/README.md) |
| 05 | Observability | [cnpe/05-observability](docs/cnpe/05-observability/README.md) |
| 06 | Secrets Management | [cnpe/06-secrets-management](docs/cnpe/06-secrets-management/README.md) |
| 07 | Ingress / Gateway API | [cnpe/07-ingress-gateway-api](docs/cnpe/07-ingress-gateway-api/README.md) |
| 08 | Multi-Tenancy | [cnpe/08-multi-tenancy](docs/cnpe/08-multi-tenancy/README.md) |
| 09 | Developer Platforms (Backstage) | [cnpe/09-developer-platforms](docs/cnpe/09-developer-platforms/README.md) |
| 10 | Security / Supply Chain | [cnpe/10-security-supply-chain](docs/cnpe/10-security-supply-chain/README.md) |
| 11 | IaC (Terraform/Crossplane) | [cnpe/11-iac-terraform-crossplane](docs/cnpe/11-iac-terraform-crossplane/README.md) |
| 12 | Scaling (Karpenter/KEDA) | [cnpe/12-scaling-karpenter-keda](docs/cnpe/12-scaling-karpenter-keda/README.md) |

## Prerequisites
```bash
docker --version
kubectl version --client
kind --version
```
