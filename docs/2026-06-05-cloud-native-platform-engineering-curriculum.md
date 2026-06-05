# Cloud-Native Platform Engineering — Curriculum & Plan

> The umbrella topic: **Cloud-Native Platform Engineering (CNPE)**.
> This builds directly on top of the existing **CKA / 40 Days of Kubernetes**
> notes in this repo. Kubernetes is the substrate; everything here is what you
> layer on top to run a **production-grade internal developer platform (IDP)**.

Search phrase to keep using: **"Cloud Native Platform Engineering"**.

---

## Mental model

```
                Cloud-Native Platform Engineering
                              |
        ------------------------------------------------
        |              |               |               |
    Delivery       Governance       Runtime        Experience
        |              |               |               |
    Argo CD        Kyverno        Service Mesh      Backstage
    GitOps         OPA/Gatekeeper Istio/Linkerd     Golden Paths
    Helm           Policies       Cilium            Templates
    Kustomize      Compliance     Gateway API       Dev Portal
```

### Before vs After

```
BEFORE                              AFTER
------------------------------      ------------------------------
Developers manually deploy apps     Git defines desired state
Security reviews happen late        Argo CD applies it
Networking is ad hoc                Kyverno blocks bad configs
Observability is inconsistent       Service mesh secures traffic
                                    Observability shows health
                                    Platform gives paved roads
```

---

## The four pillars → repo topics

Each topic below has its own directory under `docs/cnpe/`. We drill into them
one at a time. Kubernetes (topic `01`) is already covered by the CKA day-notes;
its folder just maps those notes into the platform context.

| # | Topic | Pillar | Folder |
|---|-------|--------|--------|
| 01 | Kubernetes Foundation | Substrate | [cnpe/01-kubernetes](cnpe/01-kubernetes/README.md) |
| 02 | GitOps / Argo CD | Delivery | [cnpe/02-gitops-argocd](cnpe/02-gitops-argocd/README.md) |
| 03 | Policy-as-Code / Kyverno | Governance | [cnpe/03-policy-as-code-kyverno](cnpe/03-policy-as-code-kyverno/README.md) |
| 04 | Service Mesh (Istio/Linkerd/Cilium) | Runtime | [cnpe/04-service-mesh](cnpe/04-service-mesh/README.md) |
| 05 | Observability | Runtime | [cnpe/05-observability](cnpe/05-observability/README.md) |
| 06 | Secrets Management | Runtime | [cnpe/06-secrets-management](cnpe/06-secrets-management/README.md) |
| 07 | Ingress / Gateway API | Runtime | [cnpe/07-ingress-gateway-api](cnpe/07-ingress-gateway-api/README.md) |
| 08 | Multi-Tenancy | Governance | [cnpe/08-multi-tenancy](cnpe/08-multi-tenancy/README.md) |
| 09 | Developer Platforms (Backstage) | Experience | [cnpe/09-developer-platforms](cnpe/09-developer-platforms/README.md) |
| 10 | Security / Supply Chain | Governance | [cnpe/10-security-supply-chain](cnpe/10-security-supply-chain/README.md) |
| 11 | IaC (Terraform/Pulumi/Crossplane) | Delivery | [cnpe/11-iac-terraform-crossplane](cnpe/11-iac-terraform-crossplane/README.md) |
| 12 | Scaling (Karpenter/KEDA/HPA/VPA) | Runtime | [cnpe/12-scaling-karpenter-keda](cnpe/12-scaling-karpenter-keda/README.md) |

---

## Recommended path (the spine)

1. **KodeKloud Platform Engineer Learning Path** — broad spine: K8s, DevOps,
   IaC, CI/CD, GitOps, observability, security.
2. **KodeKloud CNPE Course** — all-in-one, certification-style platform course.
3. **CNCF Training Courses** — official reference depth (K8s, Istio,
   observability, security, ecosystem).
4. **Platform Engineering GitOps Course** — enterprise multi-cluster,
   policy-driven GitOps, platform operating model.
5. **CNCF Platforms White Paper** — conceptual framing for IDPs & platform teams.
6. **platformengineering.org** — real platform-team practices.

### Suggested sequencing

```
Platform Engineering
   |
   +--> Argo CD / GitOps            (topic 02)
   +--> Kyverno / Policy-as-Code    (topic 03)
   +--> Istio / Service Mesh        (topic 04)
   +--> Prometheus/Grafana/OTel     (topic 05)
   +--> External Secrets / Vault    (topic 06)
   +--> Gateway API                 (topic 07)
   +--> Multi-tenancy               (topic 08)
   +--> Terraform / Crossplane      (topic 11)
   +--> Backstage / IDP             (topic 09)
   +--> Supply chain security       (topic 10)
   +--> Karpenter / KEDA            (topic 12)
```

---

## Tool map (adjacent landscape)

| Area | Tools |
|------|-------|
| GitOps | Argo CD, Flux |
| Policy-as-code | Kyverno, OPA Gatekeeper |
| Service mesh | Istio, Linkerd, Cilium Service Mesh |
| Gateway | Envoy Gateway, Kubernetes Gateway API, Kong |
| Observability | Prometheus, Grafana, OpenTelemetry, Loki |
| Secrets | External Secrets Operator, Vault, Sealed Secrets |
| IaC | Terraform, Pulumi, Crossplane |
| Dev portal | Backstage |
| Security | Trivy, Cosign, SLSA, SBOMs |
| Scaling | Karpenter, KEDA, HPA/VPA |

---

## How to use this curriculum

1. Pick a topic folder under `docs/cnpe/`.
2. Read its `README.md` (goal, why, subtopics, labs, resources, checklist).
3. Do every lab against the local `kind`/cluster we already use for CKA.
4. Commit notes + manifests as you go; keep each topic self-contained.
5. Move to the next topic in the sequencing list above.

## Checklist (program level)

- [ ] K8s foundation solid (CKA notes complete)
- [ ] GitOps loop running (Argo CD syncs from Git)
- [ ] Policies enforced (Kyverno blocks bad configs)
- [ ] mTLS + traffic management via service mesh
- [ ] Golden-signal observability in place
- [ ] Secrets sourced from a backend, never in Git plaintext
- [ ] Gateway API routing North-South traffic
- [ ] Tenants isolated (namespaces, quotas, RBAC, network policy)
- [ ] Backstage portal with golden-path templates
- [ ] Signed images + SBOMs + scanning in CI
- [ ] Infra declared as code (Terraform/Crossplane)
- [ ] Autoscaling for pods (HPA/VPA/KEDA) and nodes (Karpenter)
