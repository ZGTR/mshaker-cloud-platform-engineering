# 12 — Scaling (Karpenter / KEDA / HPA / VPA)

**Pillar:** Runtime

## Goal
Scale efficiently at both layers: workloads (pods) to match demand, and nodes
(infrastructure) to match workloads — for performance and cost.

## Why it matters
Right-sizing is where reliability meets cloud cost. Good autoscaling absorbs
spikes, scales to zero when idle, and avoids over-provisioning.

## What this covers
- Pod scaling: HPA (horizontal), VPA (vertical), and their interaction
- Event-driven scaling with KEDA (queues, Kafka, cron, custom metrics; scale-to-zero)
- Cluster Autoscaler vs Karpenter for node provisioning
- Karpenter: just-in-time, bin-packing, consolidation, spot strategy
- Metrics needed (metrics-server, custom/external metrics adapters)
- Cost awareness (Kubecost/OpenCost) and capacity planning

## Hands-on labs
- [ ] Configure HPA on CPU + a custom metric
- [ ] Enable VPA in recommend mode, review suggestions
- [ ] Use KEDA to scale a consumer on queue depth, including scale-to-zero
- [ ] Set up Karpenter (or Cluster Autoscaler) and watch nodes scale
- [ ] Add OpenCost and review cost per namespace/tenant

## Tools
HPA, VPA, KEDA, Karpenter, Cluster Autoscaler, OpenCost/Kubecost

## Resources
- keda.sh, karpenter.sh, kubernetes.io HPA/VPA docs, opencost.io

## Checklist
- [ ] Workloads scale on real demand signals
- [ ] Idle workloads scale to zero where appropriate
- [ ] Nodes scale up/down automatically and cost-efficiently
