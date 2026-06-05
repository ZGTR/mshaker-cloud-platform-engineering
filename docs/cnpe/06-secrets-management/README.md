# 06 — Secrets Management

**Pillar:** Runtime / Governance

## Goal
Keep secrets out of Git plaintext while still doing GitOps. Source secrets from
a secure backend and sync them into the cluster safely.

## Why it matters
Hardcoded or base64-only "secrets" are a top breach vector. Platforms need a
clear, auditable secret supply chain compatible with GitOps.

## What this covers
- Why native K8s Secrets are only base64 (not encrypted at rest by default)
- External Secrets Operator (ESO) syncing from a backend
- Backends: HashiCorp Vault, cloud secret managers (AWS/GCP/Azure)
- Sealed Secrets (encrypt-in-Git model) and when it fits
- Encryption at rest (KMS), rotation, and least-privilege access
- SOPS for encrypted files in Git

## Hands-on labs
- [ ] Deploy Vault (dev mode) or use a cloud secret manager
- [ ] Install External Secrets Operator and sync a secret
- [ ] Try Sealed Secrets: commit an encrypted secret to Git
- [ ] Encrypt a file with SOPS and decrypt at apply time
- [ ] Rotate a secret and confirm pods pick it up

## Tools
External Secrets Operator, Vault, Sealed Secrets, SOPS

## Resources
- external-secrets.io, vaultproject.io, github.com/bitnami-labs/sealed-secrets

## Checklist
- [ ] No plaintext secrets in Git
- [ ] Secrets sourced from a backend with audit logging
- [ ] Rotation path documented and tested
