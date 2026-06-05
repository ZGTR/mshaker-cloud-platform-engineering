# 01 — Kubernetes Foundation

**Pillar:** Substrate · **Status:** covered by existing CKA notes.

## Goal
Be fluent operating Kubernetes: the substrate every other platform capability
runs on. This folder maps the repo's CKA day-notes into the platform context.

## Why it matters
You cannot build a platform on top of an orchestrator you don't understand.
GitOps, mesh, policy, and observability all assume confident K8s operations.

## What this covers (already in repo)
- Containers & images (Docker, multi-stage builds)
- Cluster architecture, control plane, nodes
- Workloads: Pods, Deployments, ReplicaSets, DaemonSets, Jobs/CronJobs
- Services, namespaces, multi-container patterns
- Scheduling: taints/tolerations, affinity, requests/limits
- Autoscaling (HPA/VPA), health probes, ConfigMaps & Secrets

See `../../2026-06-05-day-*.md` (Days 0–19) and the root `README.md` index.

## Platform-context labs
- [ ] Stand up a multi-node `kind` cluster used by every later topic
- [ ] Create a `platform` and a `tenant-a` namespace with quotas
- [ ] Deploy a sample app declaratively (becomes the GitOps source app)

## Resources
- CNCF training, kubernetes.io/docs
- This repo's CKA notes (Days 0–40)

## Checklist
- [ ] Comfortable with `kubectl` core verbs and YAML authoring
- [ ] Can troubleshoot a failing pod end-to-end
- [ ] Local cluster ready for the rest of the curriculum
