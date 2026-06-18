# Day 0 — CKA Course Intro & Roadmap

> Video: FREE Kubernetes Full Course (Day 0/40) — CKA Tutorial + Roadmap
> https://www.youtube.com/watch?v=6_gMoe7Ik8k
> Duration: ~12 min

## Problem & solution
Kubernetes is huge and the CKA is a hands-on, performance-based exam, so
unstructured studying wastes time and leaves dangerous gaps. Learners need a
clear roadmap and accurate expectations of the exam format before diving in.

**Solution:** Follow the 40-day path in order, Docker basics first, then core objects, scheduling, security, cluster ops, and troubleshooting, practicing hands-on each day toward the CKA.

## Goal of this video
Set expectations for the **40 Days of Kubernetes** challenge and explain the
path to passing the **CKA (Certified Kubernetes Administrator)** exam.

## What is the CKA exam?
- Hands-on, **performance-based** exam (you operate a real cluster, no MCQs).
- ~2 hours, 15–20 tasks, run on a live terminal.
- Passing score ~66%. Open book: only `kubernetes.io/docs` allowed.
- Tests you on real `kubectl` speed, YAML authoring, and troubleshooting.

## The 40-Day learning path (ASCII map)
The challenge groups the syllabus into **five phases** that build on each other,
from containers up through storage and ops.

```
                         40 DAYS OF KUBERNETES
                         =====================

  PHASE 1: CONTAINERS (Day 1-3)
  +-----------------------------------------------+
  | Docker basics -> Dockerize app -> Multi-stage  |
  +-----------------------------------------------+
                         |
                         v
  PHASE 2: K8S CORE (Day 4-13)
  +-----------------------------------------------+
  | Why K8s -> Architecture -> Cluster setup ->    |
  | Pods -> Deployments -> Services -> Namespaces  |
  | -> Multi-container -> DaemonSet/Job            |
  +-----------------------------------------------+
                         |
                         v
  PHASE 3: SCHEDULING & CONFIG (Day 13-19)
  +-----------------------------------------------+
  | Static pods -> Taints -> Affinity -> Requests  |
  | /Limits -> Autoscaling -> Probes -> ConfigMap  |
  +-----------------------------------------------+
                         |
                         v
  PHASE 4: SECURITY (Day 20-26)
  +-----------------------------------------------+
  | TLS -> Certs -> AuthN/AuthZ -> RBAC ->         |
  | ServiceAccounts -> Network Policies            |
  +-----------------------------------------------+
                         |
                         v
  PHASE 5: STORAGE, NET, OPS (Day 27-40)
  +-----------------------------------------------+
  | kubeadm -> Volumes/PV/PVC -> DNS/CoreDNS ->    |
  | CNI -> Ingress -> Upgrade -> etcd backup ->    |
  | Logging -> Troubleshooting -> JSONPath -> Exam |
  +-----------------------------------------------+
```

## How to study (per day)
1. Watch the video.
2. Read the matching doc here.
3. Reproduce every command in your own cluster.
4. Do the assignment / post notes publicly (`#40daysofkubernetes`).

## Prerequisites to install
- Docker Desktop (or Docker Engine on Linux)
- `kubectl`
- `kind` (Kubernetes IN Docker) for a local multi-node cluster

```bash
# verify after install
docker --version
kubectl version --client
kind --version
```

## Key takeaways
- CKA = **practice**, not memorization. Build muscle memory with `kubectl`.
- Master Docker first; Kubernetes orchestrates containers.
- Learn to navigate `kubernetes.io/docs` fast (you get it during the exam).

## Checklist
- [ ] Tools installed and verified
- [ ] Understand exam format (hands-on, 2h, docs allowed)
- [ ] Committed to the 40-day plan
