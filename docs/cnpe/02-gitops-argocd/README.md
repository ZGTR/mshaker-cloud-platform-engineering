# 02 — GitOps / Argo CD

**Pillar:** Delivery

## Goal
Make Git the single source of truth. Argo CD continuously reconciles cluster
state to match the desired state declared in Git.

## Why it matters
Manual `kubectl apply` does not scale and is not auditable. GitOps gives you
declarative delivery, drift detection, rollbacks, and a clear audit trail.

## What this covers
- GitOps principles (declarative, versioned, pulled, continuously reconciled)
- Argo CD architecture: Application, ApplicationSet, Projects, sync waves
- App-of-apps pattern; multi-cluster, multi-environment promotion
- Helm + Kustomize as Argo CD sources
- Health/sync status, self-heal, automated vs manual sync
- Flux as the alternative; when to choose which

## Hands-on labs
- [ ] Install Argo CD into the cluster
- [ ] Create an Application pointing at a Git repo of manifests
- [ ] Demonstrate drift detection + self-heal (edit live, watch revert)
- [ ] Use ApplicationSet to fan out across namespaces/clusters
- [ ] Promote dev → staging with sync waves

## Tools
Argo CD, Flux, Helm, Kustomize

## Resources
- argo-cd.readthedocs.io, fluxcd.io
- OpenGitOps principles (opengitops.dev)

## Checklist
- [ ] Cluster state driven entirely from Git
- [ ] Rollback by reverting a commit
- [ ] App-of-apps managing the whole platform
