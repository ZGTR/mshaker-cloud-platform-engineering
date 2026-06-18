# Follow-up — Provision a PRODUCTION kubeadm cluster with Pulumi (AWS / GCP)

> Companion to Day 27 (`2026-06-05-day-27-kubeadm-cluster-setup.md`).
> Same HA cluster as the Terraform doc
> (`2026-06-05-day-27-kubeadm-cluster-setup-aws-gcp-terraform.md`), in Pulumi.

## Problem & solution
Building an HA kubeadm cluster by hand (or by clicking through a cloud console)
is slow, easy to get wrong, undocumented, and impossible to reproduce the same
way twice across AWS, GCP, or staging vs prod.

**Solution:** Express the whole topology — network, internal LB, firewall, and
role-aware nodes that run kubeadm with a secure join handshake — as Pulumi
(TypeScript), so the cluster is reproducible, reviewable, and the role-aware
logic is just normal code.

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
Extra control-plane nodes and workers need the cluster CA hash + a token that
only exist *after* `control-plane-0` inits. How you deliver them differs between
a lab and production.

**Lab / throwaway clusters (NOT production).** Learning locally (kind, Vagrant,
a scratch VM you will delete)? Convenience is fine: pre-share a static `kubeadm
token` or skip CA verification with
`--discovery-token-unsafe-skip-ca-verification`. This is acceptable *only*
because the cluster is disposable and not exposed. **Never** carry this shortcut
into a real environment — skipping the CA hash lets a joining node trust any API
server that answers (a man-in-the-middle hole).

**Production (this is what the IaC below does).** **Do not** pre-share a static
token and **do not** use `--discovery-token-unsafe-skip-ca-verification`. Have
`control-plane-0` publish short-lived material to a secret store; joining nodes
read it on boot.

```bash
# control-plane-0 startup script, after kubeadm init:
HASH=$(openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey \
       | openssl rsa -pubin -outform DER 2>/dev/null \
       | sha256sum | awk '{print "sha256:"$1}')
TOKEN=$(kubeadm token create --ttl 2h)
CERTKEY=$(kubeadm init phase upload-certs --upload-certs | tail -1)
# publish to AWS SSM SecureString or GCP Secret Manager, then joiners read them.
```
> Tokens are short-lived: mint them at join/scale-out time, not once up front.

## Ports the firewall must allow
```
   TCP 6443         kube-apiserver           (LB + admin CIDR -> control plane)
   TCP 2379-2380    etcd                      (control plane <-> control plane)
   TCP 10250        kubelet API               (all nodes, intra-cluster)
   TCP 10257/10259  controller-mgr/scheduler  (control plane, intra-cluster)
   TCP 30000-32767  NodePort services         (only if used; prefer LB/Ingress)
   TCP 179          Calico BGP                (between all nodes)
   TCP 22           SSH                        (bastion/SSM ONLY, not the internet)
   + allow all traffic inside the pod CIDR (192.168.0.0/16) between nodes
```

## AWS (EC2 + internal NLB)
Pulumi expresses the same resources in a general-purpose language (TypeScript),
so the role-aware loop is just normal code. Private subnets, an internal NLB for
the API, a tightly-scoped security group, and SSM (no open SSH).

```ts
import * as aws from "@pulumi/aws";
import * as fs from "fs";

const adminCidr = config.require("adminCidr");        // VPN/office CIDR, not 0/0
const privateSubnetIds: string[] = config.requireObject("privateSubnetIds");

// API SG: intra-cluster (self) + admin to 6443 only
const cpSg = new aws.ec2.SecurityGroup("kubeadm-cp", {
  vpcId,
  ingress: [
    { description: "intra-cluster", protocol: "-1", fromPort: 0, toPort: 0, self: true },
    { description: "admin to API", protocol: "tcp", fromPort: 6443, toPort: 6443, cidrBlocks: [adminCidr] },
  ],
  egress: [{ protocol: "-1", fromPort: 0, toPort: 0, cidrBlocks: ["0.0.0.0/0"] }],
});

// internal NLB owning the controlPlaneEndpoint
const nlb = new aws.lb.LoadBalancer("kubeadm-api", {
  internal: true, loadBalancerType: "network", subnets: privateSubnetIds,
});
const tg = new aws.lb.TargetGroup("kubeadm-api", {
  port: 6443, protocol: "TCP", vpcId, healthCheck: { protocol: "TCP", port: "6443" },
});
new aws.lb.Listener("kubeadm-api", {
  loadBalancerArn: nlb.arn, port: 6443, protocol: "TCP",
  defaultActions: [{ type: "forward", targetGroupArn: tg.arn }],
});

const bootstrap = fs.readFileSync("bootstrap.sh", "utf8");
const render = (role: string) =>
  nlb.dnsName.apply(dns => bootstrap
    .replace("__ROLE__", role)
    .replace("__CP_ENDPOINT__", `${dns}:6443`)
    .replace("__SECRET_PREFIX__", "/k8s/join"));

// 3 control-plane nodes, one per AZ
for (let i = 0; i < 3; i++) {
  const cp = new aws.ec2.Instance(`control-plane-${i}`, {
    ami: ubuntuAmi, instanceType: "t3.large", subnetId: privateSubnetIds[i],
    vpcSecurityGroupIds: [cpSg.id], sourceDestCheck: false,
    iamInstanceProfile: nodeProfile.name,                       // SSM + secrets
    rootBlockDevice: { volumeSize: 50, encrypted: true },
    userData: render(i === 0 ? "init" : "join-cp"),
    tags: { Name: `control-plane-${i}` },
  });
  new aws.lb.TargetGroupAttachment(`cp-${i}`, { targetGroupArn: tg.arn, targetId: cp.id });
}

// worker pool (use an ASG in real life)
for (let i = 0; i < workerCount; i++) {
  new aws.ec2.Instance(`worker-${i}`, {
    ami: ubuntuAmi, instanceType: "t3.large", subnetId: privateSubnetIds[i % 3],
    vpcSecurityGroupIds: [cpSg.id], sourceDestCheck: false,
    iamInstanceProfile: nodeProfile.name,
    rootBlockDevice: { volumeSize: 80, encrypted: true },
    userData: render("join-worker"),
    tags: { Name: `worker-${i}` },
  });
}
```
> The instance profile grants **SSM Session Manager** (no open port 22) and read
> access to the `/k8s/join/*` SecureString parameters.

## GCP (Compute Engine + internal TCP LB)
Identical idea, different nouns: an internal VIP for the API, a firewall scoped
to the cluster network + admin range, and control-plane instances with no public
IP.

```ts
import * as gcp from "@pulumi/gcp";

new gcp.compute.Firewall("kubeadm-intra", {
  network, sourceTags: ["kubeadm"], targetTags: ["kubeadm"],
  allows: [
    { protocol: "tcp", ports: ["2379-2380","10250","10257","10259","179","6443","30000-32767"] },
    { protocol: "udp", ports: ["8472"] },
  ],
});
new gcp.compute.Firewall("kubeadm-admin-api", {
  network, sourceRanges: [adminCidr], targetTags: ["kubeadm"],   // not 0.0.0.0/0
  allows: [{ protocol: "tcp", ports: ["6443"] }],
});

const apiVip = new gcp.compute.Address("kubeadm-api", {
  addressType: "INTERNAL", subnetwork,
});

const bootstrap = fs.readFileSync("bootstrap.sh", "utf8");
for (let i = 0; i < 3; i++) {
  new gcp.compute.Instance(`control-plane-${i}`, {
    machineType: "e2-standard-2", zone: zones[i], tags: ["kubeadm"],
    bootDisk: { initializeParams: { image: "ubuntu-os-cloud/ubuntu-2204-lts", size: 50 } },
    networkInterfaces: [{ network, subnetwork }],   // no accessConfigs = no public IP
    canIpForward: true,
    serviceAccount: { scopes: ["cloud-platform"] }, // read Secret Manager
    metadataStartupScript: apiVip.address.apply(ip => bootstrap
      .replace("__ROLE__", i === 0 ? "init" : "join-cp")
      .replace("__CP_ENDPOINT__", `${ip}:6443`)
      .replace("__SECRET_PREFIX__", "k8s-join")),
  });
}
// + gcp.compute.RegionBackendService / ForwardingRule on :6443 -> the cp group
```
> No `accessConfigs` = no public IP. Reach nodes via IAP/bastion; the
> `cloud-platform` scope lets the startup script read the join secrets.

## Managed alternative
See `examples/agent-state-service/iac/{aws,gcp}` for the repo's managed EKS/GKE
example (Terraform). A managed control plane runs, patches, and backs up etcd
for you — removing the HA + backup + join-handshake burden. Prefer it unless you
specifically need self-managed kubeadm.

## Key takeaway
Pulumi or Terraform, the lesson is the same: **infra is the easy part; the
secure join is what needs a plan.** Internal LB for the API, private subnets, a
tightly-scoped firewall, and short-lived join material via a secret store.
