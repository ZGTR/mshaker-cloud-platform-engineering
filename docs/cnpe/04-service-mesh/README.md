# 04 — Service Mesh (Istio / Linkerd / Cilium)

**Pillar:** Runtime

## Goal
Secure, observe, and control service-to-service traffic without changing app
code: mTLS, traffic shifting, retries, and request-level telemetry.

## Why it matters
East-West traffic is where reliability and zero-trust security live. A mesh
gives uniform mTLS, fine-grained traffic policy, and golden-signal metrics.

## What this covers
- Sidecar vs sidecarless (Istio ambient, Cilium eBPF) architectures
- mTLS / zero-trust identity (SPIFFE/SVID)
- Traffic management: canary, blue-green, traffic splitting, retries, timeouts
- Resilience: circuit breaking, fault injection
- Mesh observability (metrics, traces) and how it feeds topic 05
- Choosing: Istio (features) vs Linkerd (simplicity) vs Cilium (eBPF/network)

## Hands-on labs
- [ ] Install a mesh (start with Linkerd or Istio ambient)
- [ ] Enforce mTLS between two services
- [ ] Canary a new version with weighted traffic split
- [ ] Inject faults and verify retries/timeouts
- [ ] View the mesh topology + golden signals

## Tools
Istio, Linkerd, Cilium Service Mesh

## Resources
- istio.io, linkerd.io, cilium.io

## Checklist
- [ ] mTLS enabled mesh-wide
- [ ] Progressive delivery via traffic shifting
- [ ] Mesh metrics flowing into observability stack
