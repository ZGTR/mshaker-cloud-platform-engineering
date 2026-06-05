# 09 — Developer Platforms (Backstage / IDP)

**Pillar:** Experience

## Goal
Give developers paved roads: self-service golden paths, software templates, and
a portal that hides platform complexity behind a great experience.

## Why it matters
All the runtime/governance machinery only pays off if developers can use it
easily. The Internal Developer Platform (IDP) is the product; devs are the users.

## What this covers
- IDP concepts (CNCF Platforms White Paper) and the platform-as-product mindset
- Backstage: software catalog, TechDocs, plugins, the developer portal
- Software Templates / Scaffolder = golden paths (new service in minutes)
- Connecting Backstage to GitOps (Argo CD), CI, and observability
- Measuring platform success (DORA, adoption, time-to-first-deploy)
- Alternatives: Port, Cortex, Humanitec, Backstage-based distros

## Hands-on labs
- [ ] Deploy Backstage and register existing services in the catalog
- [ ] Build a Software Template that scaffolds repo + manifests + Argo CD app
- [ ] Surface Argo CD sync status + Grafana dashboards in the portal
- [ ] Add TechDocs for a service
- [ ] Define one golden path end-to-end (commit → running service)

## Tools
Backstage, Port, Cortex, Humanitec

## Resources
- backstage.io, CNCF Platforms White Paper, platformengineering.org

## Checklist
- [ ] Self-service "create a new service" path works
- [ ] Catalog reflects real ownership
- [ ] Devs get status/observability without leaving the portal
