# 11 — Infrastructure as Code (Terraform / Pulumi / Crossplane)

**Pillar:** Delivery

## Goal
Declare and provision infrastructure — clusters, networks, databases, cloud
resources — as versioned code, ideally reconciled the same GitOps way as apps.

## Why it matters
Click-ops infrastructure is unrepeatable and undocumented. IaC makes infra
reproducible, reviewable, and recoverable; Crossplane brings it into K8s/GitOps.

## What this covers
- Terraform core: providers, state, modules, plan/apply, remote state
- Pulumi as the general-purpose-language alternative
- Crossplane: provision cloud infra via K8s CRDs (Compositions, Claims, XRDs)
- Why Crossplane + Argo CD = unified app + infra GitOps
- State management, drift, and policy on infra (OPA/Checkov/tfsec)
- Building platform abstractions (a "Database" claim devs can self-serve)

## Hands-on labs
- [ ] Provision a resource with Terraform + remote state
- [ ] Refactor it into a reusable module
- [ ] Install Crossplane and a provider
- [ ] Define a Composition + Claim so a dev can request infra via YAML
- [ ] Reconcile infra through Argo CD (GitOps for infra)

## Tools
Terraform, Pulumi, Crossplane, tfsec/Checkov

## Resources
- terraform.io, pulumi.com, crossplane.io

## Checklist
- [ ] Infra fully declared in Git
- [ ] Self-service infra claim works for a dev
- [ ] Infra changes reviewed + policy-checked before apply
