# 07 — Ingress / Gateway API

**Pillar:** Runtime

## Goal
Route North-South (external) traffic into the platform with a modern, portable,
role-oriented API: the Kubernetes Gateway API.

## Why it matters
Ingress was limited and annotation-heavy. Gateway API is the successor:
expressive, vendor-neutral, and splits responsibilities between infra and app
teams cleanly.

## What this covers
- Ingress recap and its limitations
- Gateway API resources: GatewayClass, Gateway, HTTPRoute, TLSRoute, etc.
- Role split: infra owns Gateway, app teams own Routes
- Implementations: Envoy Gateway, Istio, Kong, Contour, NGINX Gateway Fabric
- TLS termination, header/path routing, traffic splitting at the edge
- How edge routing relates to the service mesh (topic 04)

## Hands-on labs
- [ ] Install Gateway API CRDs + an implementation (e.g. Envoy Gateway)
- [ ] Define a GatewayClass + Gateway with a TLS listener
- [ ] Route two apps via HTTPRoute (host/path based)
- [ ] Do a weighted split across two backend versions
- [ ] Hand a Route to a "tenant" team while infra keeps the Gateway

## Tools
Kubernetes Gateway API, Envoy Gateway, Kong, Contour, NGINX Gateway Fabric

## Resources
- gateway-api.sigs.k8s.io, gateway.envoyproxy.io

## Checklist
- [ ] External traffic enters via Gateway API
- [ ] TLS terminated correctly
- [ ] Infra/app responsibility split enforced
