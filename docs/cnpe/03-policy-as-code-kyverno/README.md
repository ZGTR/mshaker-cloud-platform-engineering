# 03 — Policy-as-Code / Kyverno

**Pillar:** Governance

## Goal
Enforce security, compliance, and consistency automatically. Bad configs are
blocked or mutated at admission time — not caught in a late manual review.

## Why it matters
Guardrails let developers move fast safely. Policy-as-code makes governance
versioned, testable, and consistent across every cluster.

## What this covers
- Admission control: validating, mutating, generating policies
- Kyverno policies in YAML (no new language to learn)
- OPA Gatekeeper + Rego as the alternative
- Common policies: require limits, block `:latest`, enforce labels,
  disallow privileged pods, require signed images
- Policy reporting, audit vs enforce modes
- Testing policies in CI before they hit the cluster

## Hands-on labs
- [ ] Install Kyverno
- [ ] Validate: reject pods missing resource limits
- [ ] Mutate: auto-inject default labels/securityContext
- [ ] Generate: create a default NetworkPolicy per new namespace
- [ ] Compare with an equivalent Gatekeeper/Rego policy

## Tools
Kyverno, OPA Gatekeeper

## Resources
- kyverno.io, open-policy-agent.github.io/gatekeeper

## Checklist
- [ ] Non-compliant workloads rejected at admission
- [ ] Policies stored in Git and synced via Argo CD
- [ ] Policy report dashboard reviewed
