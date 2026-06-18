# Day 27 — Production Multi-Node Cluster with kubeadm

> Video: Day 27/40 — Setup a Multi-Node Kubernetes Cluster Using kubeadm
> https://www.youtube.com/watch?v=WcdMC3Lj4tU
> Duration: ~40 min

## Key terms
| Term | Meaning |
| --- | --- |
| kubeadm | Tool that bootstraps a cluster |
| Control plane | api-server / etcd / scheduler / controller-manager |
| HA | High availability (multiple control-plane nodes) |
| controlPlaneEndpoint | Stable LB address for the API |
| Join token | Short-lived credential to join nodes |
| CA cert hash | Verifies the cluster CA when joining |
| containerd | The container runtime |
| CNI | Pod network plugin (Calico here) |
| --upload-certs / certificate-key | Share control-plane certs to joiners |

## Problem & solution
kind clusters run inside Docker and aren't real production clusters. A single
control-plane node is also not production: if it dies, the whole cluster is
unmanageable and etcd data is at risk. A production cluster needs a
**highly-available control plane** (odd number of nodes for etcd quorum) behind
a load balancer, locked-down networking, encryption and auditing, and a secure
node-join process — all of which `kubeadm` can bootstrap.

**Solution:** Bootstrap a real HA cluster with kubeadm, init the control plane behind a load balancer and join more control-plane and worker nodes, with encryption, audit, and etcd backups.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== kubeadm init bootstraps the control plane      | |
   | +----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                 |
   | |    <== kubeadm join adds worker nodes          |                 |
   | | + namespace: default +                         |                 |
   | | | +----- POD -----+  |                         |                 |
   | | | | + CONTAINER + |  |                         |                 |
   | | | | | app       | |  |                         |                 |
   | | | | +-----------+ |  |                         |                 |
   | | | +---------------+  |                         |                 |
   | | +--------------------+                         |                 |
   | +------------------------------------------------+                 |
   +--------------------------------------------------------------------+
```

## What is kubeadm
`kubeadm` bootstraps a **real** (not kind) cluster: it installs the control-plane
components and gives you the commands to join more control-plane and worker
nodes. It does **not** provision infrastructure, install a CNI, or configure
backups — those are your responsibility (see the IaC follow-ups and Day-2 ops).

```
   control plane:  kube-apiserver  etcd  controller-manager  scheduler
   node tools:     kubeadm  kubelet  kubectl
   container rt:   containerd (systemd cgroup driver)
   CNI:            installed separately (Calico) for pod networking
```

## Production topology (HA)
Run **three** control-plane nodes (so etcd keeps quorum if one fails) spread
across three availability zones, fronted by a load balancer that owns the
`controlPlaneEndpoint`. Workers are a separate, scalable pool.

```
                         +-------------------------+
   admin / kubectl  -->  |  control-plane LB :6443 |   (internal/private NLB/ILB)
   (via bastion/VPN)     +------------+------------+
                                      | 6443
        +-----------------------------+-----------------------------+
        |                             |                             |
 +------v------+               +------v------+               +------v------+
 | control-1   |               | control-2   |               | control-3   |
 | apiserver   |               | apiserver   |               | apiserver   |
 | etcd  <=====|==== raft =====|==> etcd <===|==== raft =====|==> etcd     |
 | sched/ctrl  |               | sched/ctrl  |               | sched/ctrl  |
 +------+------+               +------+------+               +------+------+
   AZ-a |                        AZ-b |                        AZ-c |
        +-----------------------------+-----------------------------+
                                      |
              +-----------------------+-----------------------+
              |                       |                       |
       +------v------+         +------v------+         +------v------+
       |  worker-1   |         |  worker-2   |         |  worker-N   |
       |  kubelet    |         |  kubelet    |         |  (autoscaled |
       |  containerd |         |  containerd |         |   node pool) |
       +-------------+         +-------------+         +-------------+
```
> Quorum needs an **odd** count: 3 control-plane nodes tolerate 1 loss, 5
> tolerate 2. Two is worse than one (no majority). Keep workloads **off** the
> control plane (the default `node-role.kubernetes.io/control-plane` taint).

## The setup flow at a glance
Every node runs the **same prep** (steps 1-6). Only the final step differs by
role: the first control-plane **inits**, the other control-plane nodes **join as
control plane**, and workers **join** as workers.

```
                  +-------------------------------+
                  |  Provision N VMs across 3 AZs |
                  |  3 control-plane + M workers  |
                  +---------------+---------------+
                                  |
                  +---------------v-----------------------+
                  | Private net + LB(6443) + firewall +   |
                  | bastion/SSM for admin access          |
                  +---------------+-----------------------+
                                  |
                  +---------------v-----------------------+
                  | SAME prep on EVERY node (steps 1-6)   |
                  | swap off | kernel | containerd | runc |
                  | CNI bins | kubeadm+kubelet+kubectl     |
                  +---------------+-----------------------+
                                  |
        +-------------------------+-------------------------+
        |                         |                         |
 +------v---------+      +--------v----------+     +--------v---------+
 | first control  |      | other control     |     |   workers        |
 | plane          |      | plane (2 more)     |     |   (M nodes)      |
 +----------------+      +-------------------+     +------------------+
 | kubeadm init   |      | kubeadm join      |     | kubeadm join     |
 |  --config      |      |  --control-plane  |     |  <token> + CA    |
 |  --upload-certs|      |  --certificate-key|     |  hash            |
 +------+---------+      +--------+----------+     +--------+---------+
        |                         |                         |
        +-------------------------+-------------------------+
                                  |
                       +----------v-----------+
                       | install CNI (once)   |
                       | kubectl get nodes -> |
                       |   all Ready          |
                       +----------------------+
```

## What each common step does (and why)
Steps 1-6 run on **every** node (control plane and workers); they turn a bare VM
into one the kubelet can actually run containers on.

1. **Disable swap** — the kubelet refuses to start while swap is on. Kubernetes
   schedules and enforces memory limits against *real* RAM; swap hides memory
   pressure and breaks those guarantees. `swapoff -a` now, and comment it out in
   `/etc/fstab` so it stays off across reboots.
2. **Update kernel params** — load `overlay` + `br_netfilter` and set sysctls:
   `ip_forward=1` lets the node route pod traffic between interfaces, and
   `bridge-nf-call-iptables=1` makes bridged pod traffic visible to iptables —
   which is how kube-proxy and the CNI enforce Services and NetworkPolicies.
   Skip this and pod networking silently breaks.
3. **Install container runtime (containerd)** — Kubernetes does not run
   containers itself; the kubelet talks to a CRI runtime. containerd pulls
   images and manages the container lifecycle. Use the **systemd** cgroup driver
   in production so the kubelet and runtime agree on one cgroup manager.
4. **Install runc** — the low-level OCI runtime containerd calls to actually
   spawn the container process with namespaces + cgroups. containerd is the
   manager; runc is what creates the real process.
5. **Install CNI plugins** — the binaries in `/opt/cni/bin` that wire each pod's
   network namespace (assign an IP, create the veth pair, set routes). Calico
   drops its config here. No CNI means pods stay `ContainerCreating` and nodes
   stay `NotReady`.
6. **Install kubeadm + kubelet + kubectl** — `kubelet` is the node agent that
   watches PodSpecs and drives containerd; `kubeadm` is the bootstrap tool
   (`init` / `join`); `kubectl` is the CLI that talks to the api-server. **Pin
   and hold the versions** so an unattended `apt upgrade` can't skew the cluster.

Only **step 7** differs by role: the first control-plane runs `kubeadm init`,
the other two run `kubeadm join --control-plane`, and workers run `kubeadm join`.

## Prep — run on ALL nodes (control plane + workers)
Before kubeadm runs, every node needs swap off, kernel modules loaded, and a
properly-configured container runtime — otherwise the kubelet won't start.

```bash
# 1. disable swap (kubelet requires it off)
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 2. enable IPv4 forwarding + let iptables see bridged traffic
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay && sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# 3. containerd with the systemd cgroup driver (REQUIRED in production)
sudo apt-get update && sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd && sudo systemctl enable containerd

# 4. install a PINNED kubeadm/kubelet/kubectl, then HOLD them
KUBE_VERSION=1.29.6-1.1
sudo apt-get install -y kubelet=$KUBE_VERSION kubeadm=$KUBE_VERSION kubectl=$KUBE_VERSION
sudo apt-mark hold kubelet kubeadm kubectl containerd
sudo systemctl enable --now kubelet

# 5. point crictl at containerd
sudo crictl config runtime-endpoint unix:///var/run/containerd/containerd.sock
```
> Pin one minor version cluster-wide. Upgrades are a deliberate, one-minor-at-a-
> time operation (`kubeadm upgrade`), never an accidental `apt upgrade`.

## Secure cluster config (encryption + audit)
Before initializing, prepare two things production clusters must not skip:
**encryption at rest for Secrets** and an **audit policy**.

```yaml
# /etc/kubernetes/enc/enc.yaml  -- encrypts Secrets in etcd
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64 of 32 random bytes: head -c32 /dev/urandom | base64>
      - identity: {}        # allows reading older unencrypted Secrets
```

```yaml
# /etc/kubernetes/audit/policy.yaml  -- minimal sane audit policy
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata        # who did what, when (no request bodies by default)
```

The kubeadm cluster config wires these in and sets the HA endpoint:

```yaml
# kubeadm-config.yaml  -- run on the FIRST control-plane node
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
kubernetesVersion: v1.29.6
controlPlaneEndpoint: "k8s-api.internal.example.com:6443"   # the LB DNS/VIP
networking:
  podSubnet: 192.168.0.0/16
apiServer:
  extraArgs:
    encryption-provider-config: /etc/kubernetes/enc/enc.yaml
    audit-policy-file: /etc/kubernetes/audit/policy.yaml
    audit-log-path: /var/log/kubernetes/audit/audit.log
    audit-log-maxage: "30"
    audit-log-maxbackup: "10"
  extraVolumes:
    - { name: enc,   hostPath: /etc/kubernetes/enc,        mountPath: /etc/kubernetes/enc,        readOnly: true }
    - { name: audit, hostPath: /etc/kubernetes/audit,      mountPath: /etc/kubernetes/audit,      readOnly: true }
    - { name: alog,  hostPath: /var/log/kubernetes/audit,  mountPath: /var/log/kubernetes/audit }
etcd:
  local:
    extraArgs:
      auto-compaction-retention: "8"      # hourly compaction
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cgroupDriver: systemd                     # must match containerd
```

## Initialize the FIRST control-plane node
`--upload-certs` stores the control-plane certs in a temporary Secret so the
other control-plane nodes can pull them during join.

```bash
sudo kubeadm init --config kubeadm-config.yaml --upload-certs
```
This prints **two** join commands: one for control-plane nodes (includes
`--control-plane --certificate-key`) and one for workers. Save both.

Set up kubeconfig for your admin user (or fetch `/etc/kubernetes/admin.conf`
through your bastion/secret store rather than copying it around):
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Install the CNI (Calico) **once**, from the first control-plane node:
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml
# ensure custom-resources.yaml CIDR matches podSubnet (192.168.0.0/16)
kubectl apply -f custom-resources.yaml
```

## Join the other control-plane nodes
Run the prep on each, then the **control-plane** join command from `init`:
```bash
sudo kubeadm join k8s-api.internal.example.com:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane --certificate-key <certificate-key>
```
> The uploaded certs and the `--certificate-key` **expire after ~2 hours**. To
> add a control-plane node later, re-upload them: `sudo kubeadm init phase
> upload-certs --upload-certs` (prints a fresh key).

## Join the workers — the secure way
**Lab / throwaway clusters (NOT production):** for a disposable local cluster
you may use a static token or `--discovery-token-unsafe-skip-ca-verification`
for speed. Never carry that into a real environment — skipping the CA hash lets
a node trust any API server that answers (a man-in-the-middle hole).

**Production:** never use `--discovery-token-unsafe-skip-ca-verification`. Always
pass a real CA hash and a **short-lived** token generated on demand:

```bash
# on a control-plane node: fresh 2h token + a complete, verified join command
kubeadm token create --ttl 2h --print-join-command

# the CA hash by hand if you need it separately:
openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey \
  | openssl rsa -pubin -outform DER 2>/dev/null \
  | sha256sum | awk '{print "sha256:"$1}'
```
Then on each worker:
```bash
sudo kubeadm join k8s-api.internal.example.com:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```
> For automated/IaC node bootstrap, have the first control-plane publish the CA
> hash (and a freshly minted token) to **AWS SSM Parameter Store / GCP Secret
> Manager**, and have joining nodes read them at startup. Tokens are short-lived,
> so generate them at scale-out time, not once up front.

## Production hardening checklist
- [ ] **Three** control-plane nodes across 3 AZs; LB owns `controlPlaneEndpoint`.
- [ ] etcd **encryption at rest** enabled (`EncryptionConfiguration`); back up the key.
- [ ] **Audit logging** enabled and shipped off-node.
- [ ] Firewall/SG restricts 6443 to the LB + admin CIDR; **no `0.0.0.0/0`**;
      SSH only via bastion/SSM, not open to the internet.
- [ ] Nodes in **private subnets**; egress via NAT only.
- [ ] Versions **pinned + held**; upgrades via `kubeadm upgrade`, one minor at a time.
- [ ] containerd uses the **systemd** cgroup driver (matches kubelet).
- [ ] Control-plane taint left in place (no workloads on control plane).
- [ ] RBAC reviewed; anonymous auth off (kubeadm default); kubelet authz = Webhook.
- [ ] Certificate expiry monitored (`kubeadm certs check-expiration`).

## Day-2 operations
A cluster is not "done" at `Ready`. The recurring jobs:

```bash
# etcd snapshot backup (run regularly; store off-cluster)
sudo ETCDCTL_API=3 etcdctl snapshot save /var/backups/etcd-$(date +%F).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# certificate expiry (kubeadm renews on upgrade, but verify)
sudo kubeadm certs check-expiration

# controlled upgrade (one minor version at a time)
sudo kubeadm upgrade plan
```

## Validate
Confirm every node is **Ready**, etcd has a healthy quorum, and system pods run.

```bash
kubectl get nodes -o wide          # 3 control-plane + workers, all Ready
kubectl get pods -A                 # control plane + calico Running
kubectl -n kube-system get pods -l component=etcd   # one etcd per control-plane
kubectl get --raw='/readyz?verbose' # api-server self-check
```

## Troubleshooting Calico
- Disable source/dest check on every node (AWS); allow `can_ip_forward` (GCP).
- Allow **BGP TCP 179** between nodes in the firewall/security group.
- If calico-node is unhealthy, pin the autodetect interface:
```bash
kubectl set env daemonset/calico-node -n calico-system \
  IP_AUTODETECTION_METHOD=interface=ens5     # ens5 = your real NIC (ip a)
```

## Follow-ups: provision this cluster as IaC
Provisioning this exact HA kubeadm cluster as code is covered in two companion
docs. Both share the same shape (private network -> LB(6443) -> firewall for the
kubeadm ports -> control-plane + worker VMs -> role-aware startup script) and the
secure join handshake (CA hash + short-lived token via a secret store):

- **Terraform (AWS + GCP)** — `2026-06-05-day-27-kubeadm-cluster-setup-aws-gcp-terraform.md`
- **Pulumi (AWS + GCP)** — `2026-06-05-day-27-kubeadm-cluster-setup-aws-gcp-pulumi.md`

## Key takeaways
- Production = **HA control plane** (3 nodes, odd quorum) behind a load balancer.
- `kubeadm init --upload-certs` then `join --control-plane` adds control-plane
  nodes; plain `join` adds workers.
- Join securely: **CA hash + short-lived token**, never `unsafe-skip-ca-verification`.
- Turn on **encryption at rest** and **audit logging** before going live.
- Lock down networking (private subnets, restricted SG, bastion/SSM SSH).
- Day-2 matters: **etcd backups**, monitored cert expiry, controlled upgrades.

## Checklist
- [ ] Provisioned 3 control-plane + N worker VMs across 3 AZs, private subnets
- [ ] LB owns `controlPlaneEndpoint`; SG restricts the kubeadm ports
- [ ] Ran swap/kernel/containerd(systemd)/pinned-tools prep on all nodes
- [ ] `kubeadm init --config --upload-certs` with encryption + audit enabled
- [ ] Joined 2 more control-plane nodes and the workers (verified CA hash)
- [ ] Installed Calico; `kubectl get nodes` shows all nodes Ready
- [ ] Configured etcd backups and certificate-expiry monitoring
