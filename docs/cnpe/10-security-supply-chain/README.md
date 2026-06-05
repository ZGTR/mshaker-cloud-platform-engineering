# 10 — Security / Supply Chain

**Pillar:** Governance

## Goal
Trust what you ship: scan for vulnerabilities, sign artifacts, generate SBOMs,
and enforce provenance from commit to running container.

## Why it matters
Software supply-chain attacks are rising. A platform must guarantee that only
scanned, signed, provenance-verified artifacts run in production.

## What this covers
- Image/dependency scanning (Trivy, Grype) in CI and at admission
- SBOMs: SPDX / CycloneDX generation and storage
- Signing & verification with Cosign (Sigstore)
- SLSA framework: provenance and build-integrity levels
- Admission-time verification (Kyverno verifyImages, policy-controller)
- Runtime security basics (Falco) and least-privilege containers

## Hands-on labs
- [ ] Scan an image with Trivy and fail CI on criticals
- [ ] Generate an SBOM and attach it to the image
- [ ] Sign the image with Cosign; verify the signature
- [ ] Enforce "only signed images" via Kyverno at admission
- [ ] Add SLSA provenance to the build pipeline

## Tools
Trivy, Grype, Cosign/Sigstore, Syft, Falco, SLSA, Kyverno

## Resources
- aquasecurity.github.io/trivy, sigstore.dev, slsa.dev

## Checklist
- [ ] CI blocks vulnerable images
- [ ] All images signed + SBOM attached
- [ ] Cluster rejects unsigned/unscanned images
