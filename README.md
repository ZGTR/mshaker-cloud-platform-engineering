# CKA — 40 Days of Kubernetes (Study Notes)

Follow-along notes for **Certified Kubernetes Administrator (CKA)** based on the
playlist *"Certified Kubernetes Administrator Full Course For Beginners | CKA 2026"*
by [Tech Tutorials with Piyush](https://www.youtube.com/@TechTutorialswithPiyush).

Playlist: https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

Each doc has: goal, key concepts, ASCII diagrams, runnable commands, and a checklist.

## Index (Days 0–19)

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

## Prerequisites
```bash
docker --version
kubectl version --client
kind --version
```
