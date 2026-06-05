# 08 — Multi-Tenancy

**Pillar:** Governance

## Goal
Safely share one platform across many teams/tenants with isolation, fair
resource use, and self-service that doesn't compromise security.

## Why it matters
A platform's value comes from serving many teams. Without isolation you get
noisy neighbors, blast-radius incidents, and security gaps.

## What this covers
- Isolation models: namespace-per-tenant vs cluster-per-tenant vs vCluster
- RBAC, ServiceAccounts, and least privilege per tenant
- ResourceQuotas, LimitRanges, PriorityClasses for fairness
- NetworkPolicies for tenant network isolation
- Hierarchical Namespaces (HNC), Capsule, vCluster for soft multi-tenancy
- Tying tenancy to GitOps (per-tenant Argo CD Projects) and policy (Kyverno)

## Hands-on labs
- [ ] Create tenant namespaces with quotas + limit ranges
- [ ] Scope RBAC so a tenant only sees its own namespace
- [ ] Apply default-deny NetworkPolicies and allow only needed flows
- [ ] Spin up a vCluster for a stronger isolation tenant
- [ ] Wire a tenant to its own Argo CD Project + Kyverno guardrails

## Tools
RBAC, ResourceQuota, NetworkPolicy, HNC, Capsule, vCluster

## Resources
- kubernetes.io multi-tenancy docs, vcluster.com, capsule.clastix.io

## Checklist
- [ ] Tenants cannot see/affect each other
- [ ] Resource fairness enforced
- [ ] Tenant onboarding is self-service + governed
