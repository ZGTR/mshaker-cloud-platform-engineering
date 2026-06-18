# Follow-up — Provision a PRODUCTION kubeadm cluster with Terraform (AWS / GCP)

> Companion to Day 27 (`2026-06-05-day-27-kubeadm-cluster-setup.md`).
> Turns the HA "3 control-plane + N workers behind a load balancer" topology
> into Infrastructure-as-Code.

## Key terms
| Term | Meaning |
| --- | --- |
| IaC | Infrastructure as Code |
| Terraform | Declarative IaC tool (HCL) |
| HCL | HashiCorp Configuration Language |
| NLB | Network Load Balancer (internal, for the API) |
| Security group / firewall | Allowed-port rules |
| ASG | Auto Scaling Group (the worker pool) |
| SSM | AWS Systems Manager (secret store / no-SSH access) |
| controlPlaneEndpoint | The LB address owning :6443 |
| CA hash / join token | Secure join material for new nodes |

## Problem & solution
Building an HA kubeadm cluster by hand (or by clicking through a cloud console)
is slow, easy to get wrong, undocumented, and impossible to reproduce the same
way twice across AWS, GCP, or staging vs prod.

**Solution:** Express the whole topology — network, internal LB, firewall, and
role-aware nodes that run kubeadm with a secure join handshake — as Terraform,
so the cluster is reproducible, reviewable, and identical on every cloud.

## What we are building
A production HA cluster has the same IaC shape on every cloud:

```
   private network (3 AZs)
        -> internal LB on :6443  (owns controlPlaneEndpoint)
        -> firewall: kubeadm ports, restricted to LB + admin CIDR (no 0.0.0.0/0)
        -> 3 control-plane VMs + M worker VMs (private subnets)
        -> role-aware startup script:
              control-plane-0 -> kubeadm init --upload-certs
              control-plane-1,2 -> kubeadm join --control-plane
              workers          -> kubeadm join
        -> CA hash + short-lived token exchanged via a secret store
```

## The one hard part: the secure join handshake
Workers and extra control-plane nodes need the cluster CA hash (and a token)
that only exist *after* `control-plane-0` inits. How you hand those to joining
nodes is the whole question, and the answer is different for a lab and for prod.

**Lab / throwaway clusters (NOT production).** When you are learning locally
(kind, Vagrant, a scratch VM you will delete), convenience is fine: pre-share a
static `kubeadm token` baked into the bootstrap, or skip CA verification with
`--discovery-token-unsafe-skip-ca-verification`. This is acceptable *only*
because the cluster is disposable and not exposed. **Never** copy this shortcut
into a real environment — a skipped CA hash means a joining node will trust any
API server that answers, which is a textbook man-in-the-middle hole.

**Production (this is what the IaC below does).** **Do not** pre-share a static
token and **do not** use `--discovery-token-unsafe-skip-ca-verification`.
Instead, have `control-plane-0` publish short-lived material to a secret store
and have joining nodes read it:

```bash
# control-plane-0 (in its startup script, after kubeadm init):
HASH=$(openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey \
       | openssl rsa -pubin -outform DER 2>/dev/null \
       | sha256sum | awk '{print "sha256:"$1}')
TOKEN=$(kubeadm token create --ttl 2h)
CERTKEY=$(kubeadm init phase upload-certs --upload-certs | tail -1)

# AWS: aws ssm put-parameter --type SecureString --name /k8s/join/{hash,token,certkey}
# GCP: gcloud secrets versions add k8s-join-{hash,token,certkey} --data-file=-

# joining nodes read them, then:
#   control plane: kubeadm join $LB:6443 --token $TOKEN \
#       --discovery-token-ca-cert-hash $HASH --control-plane --certificate-key $CERTKEY
#   workers:       kubeadm join $LB:6443 --token $TOKEN \
#       --discovery-token-ca-cert-hash $HASH
```
> Tokens are short-lived: mint them at join/scale-out time, not once up front.
> A scale-out worker should call a small helper (Lambda/Cloud Function or the
> control plane via SSM run-command) to get a fresh token on boot.

## Ports the firewall must allow
```
   TCP 6443         kube-apiserver           (LB + admin CIDR -> control plane)
   TCP 2379-2380    etcd                      (control plane <-> control plane)
   TCP 10250        kubelet API               (all nodes, intra-cluster)
   TCP 10257/10259  controller-mgr/scheduler  (control plane, intra-cluster)
   TCP 30000-32767  NodePort services         (only if used; prefer a LB/Ingress)
   TCP 179          Calico BGP                (between all nodes)
   TCP 22           SSH                        (bastion/SSM ONLY, not the internet)
   + allow all traffic inside the pod CIDR (192.168.0.0/16) between nodes
```

## AWS (EC2 + internal NLB)
Private subnets across 3 AZs, an **internal** NLB for the API, a security group
that only admits the kubeadm ports from the cluster itself and admin CIDR, and
two role-aware node groups. The prep from Day 27 goes into `bootstrap.sh.tftpl`.

```hcl
variable "admin_cidr" {}            # your VPN/office CIDR; NOT 0.0.0.0/0
variable "private_subnet_ids" { type = list(string) }   # one per AZ

# --- API security group: self (intra-cluster) + admin to 6443 only ----------
resource "aws_security_group" "cp" {
  name   = "kubeadm-cp"
  vpc_id = var.vpc_id

  ingress { description = "intra-cluster", from_port = 0, to_port = 0,
            protocol = "-1", self = true }
  ingress { description = "admin to API", from_port = 6443, to_port = 6443,
            protocol = "tcp", cidr_blocks = [var.admin_cidr] }
  egress  { from_port = 0, to_port = 0, protocol = "-1", cidr_blocks = ["0.0.0.0/0"] }
}

# --- internal NLB owning the controlPlaneEndpoint ---------------------------
resource "aws_lb" "api" {
  name               = "kubeadm-api"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.private_subnet_ids
}
resource "aws_lb_target_group" "api" {
  name     = "kubeadm-api"
  port     = 6443
  protocol = "TCP"
  vpc_id   = var.vpc_id
  health_check { protocol = "TCP", port = "6443" }
}
resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 6443
  protocol          = "TCP"
  default_action { type = "forward", target_group_arn = aws_lb_target_group.api.arn }
}

# --- 3 control-plane nodes, one per AZ -------------------------------------
resource "aws_instance" "cp" {
  count                  = 3
  ami                    = var.ubuntu_ami         # 22.04 LTS
  instance_type          = "t3.large"             # >= 2 vCPU / 4 GiB for CP
  subnet_id              = var.private_subnet_ids[count.index]
  vpc_security_group_ids = [aws_security_group.cp.id]
  source_dest_check      = false                  # required for Calico
  iam_instance_profile   = aws_iam_instance_profile.node.name   # SSM + secrets
  root_block_device { volume_size = 50, encrypted = true }
  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", {
    role          = count.index == 0 ? "init" : "join-cp"
    cp_endpoint   = "${aws_lb.api.dns_name}:6443"
    secret_prefix = "/k8s/join"
  })
  tags = { Name = "control-plane-${count.index}" }
}
resource "aws_lb_target_group_attachment" "cp" {
  count            = 3
  target_group_arn = aws_lb_target_group.api.arn
  target_id        = aws_instance.cp[count.index].id
}

# --- worker pool (use an ASG in real life; instances shown for clarity) -----
resource "aws_instance" "worker" {
  count                  = var.worker_count
  ami                    = var.ubuntu_ami
  instance_type          = "t3.large"
  subnet_id              = var.private_subnet_ids[count.index % 3]
  vpc_security_group_ids = [aws_security_group.cp.id]
  source_dest_check      = false
  iam_instance_profile   = aws_iam_instance_profile.node.name
  root_block_device { volume_size = 80, encrypted = true }
  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", {
    role          = "join-worker"
    cp_endpoint   = "${aws_lb.api.dns_name}:6443"
    secret_prefix = "/k8s/join"
  })
  tags = { Name = "worker-${count.index}" }
}
```
> Admin access via **SSM Session Manager** (the `iam_instance_profile` above),
> so port 22 never needs to be open. The node role also grants read of the
> `/k8s/join/*` SSM parameters.

## GCP (Compute Engine + internal TCP LB)
Identical idea, different nouns: a regional internal load balancer for the API,
a firewall scoped to the cluster network + admin range, and 3 control-plane
instances across zones plus a worker MIG.

```hcl
variable "admin_cidr" {}

resource "google_compute_firewall" "intra" {
  name          = "kubeadm-intra"
  network       = var.network
  source_tags   = ["kubeadm"]
  target_tags   = ["kubeadm"]
  allow { protocol = "tcp", ports = ["2379-2380","10250","10257","10259","179","6443","30000-32767"] }
  allow { protocol = "udp", ports = ["8472"] }      # Calico VXLAN if used
}
resource "google_compute_firewall" "admin_api" {
  name          = "kubeadm-admin-api"
  network       = var.network
  source_ranges = [var.admin_cidr]                  # NOT 0.0.0.0/0
  target_tags   = ["kubeadm"]
  allow { protocol = "tcp", ports = ["6443"] }
}

resource "google_compute_instance" "cp" {
  count        = 3
  name         = "control-plane-${count.index}"
  machine_type = "e2-standard-2"
  zone         = var.zones[count.index]
  tags         = ["kubeadm"]
  boot_disk { initialize_params { image = "ubuntu-os-cloud/ubuntu-2204-lts", size = 50 } }
  network_interface { network = var.network, subnetwork = var.subnetwork }   # no access_config = no public IP
  can_ip_forward = true
  service_account { scopes = ["cloud-platform"] }   # read Secret Manager
  metadata_startup_script = templatefile("${path.module}/bootstrap.sh.tftpl", {
    role          = count.index == 0 ? "init" : "join-cp"
    cp_endpoint   = "${google_compute_address.api.address}:6443"
    secret_prefix = "k8s-join"
  })
}

resource "google_compute_address" "api" {        # internal VIP for the API LB
  name         = "kubeadm-api"
  address_type = "INTERNAL"
  subnetwork   = var.subnetwork
}
# + google_compute_region_backend_service / forwarding_rule on :6443 -> cp group
```
> No `access_config` block = **no public IP**. Reach nodes via IAP/bastion;
> the `cloud-platform` scope lets the startup script read the join secrets.

## Managed alternative
See `examples/agent-state-service/iac/{aws,gcp}` for the repo's Terraform layout
(`versions.tf`, `variables.tf`, `outputs.tf`). That example provisions
**managed** EKS/GKE — the cloud runs (and patches, and backs up) the control
plane for you, which removes the HA + etcd-backup + join-handshake burden
entirely. Prefer it unless you specifically need self-managed kubeadm.

## Key takeaway
Infra is the easy, repeatable part; the **secure join** is the bit that needs a
plan: an internal LB for the API, private subnets, a tightly-scoped firewall,
and short-lived join material exchanged through a secret store.
