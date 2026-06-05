# Day 27 — Multi-Node Cluster with kubeadm

> Video: Day 27/40 — Setup a Multi-Node Kubernetes Cluster Using kubeadm
> https://www.youtube.com/watch?v=WcdMC3Lj4tU
> Duration: ~40 min

## What is kubeadm
`kubeadm` bootstraps a **real** (not kind) cluster: it installs the control-plane
components and gives you the commands to join worker nodes.

```
   control plane:  kube-apiserver  etcd  controller-manager  scheduler
   node tools:     kubeadm  kubelet  kubectl
   container rt:   containerd
   CNI:            installed separately (Calico) for pod networking
```

## Topology for the demo
The lab uses one **control-plane** node and two **workers**, each a separate VM
with the node tooling and container runtime installed.

```
   +-------------+        +-------------+   +-------------+
   |   master    |        |  worker-1   |   |  worker-2   |
   | control     |<-------|  kubelet    |   |  kubelet    |
   | plane + CNI |  join  |  containerd |   |  containerd |
   +-------------+        +-------------+   +-------------+
   3 VMs (e.g. AWS EC2). Open the required ports between them.
```
> On Apple Silicon, **Multipass** is recommended over VirtualBox. On AWS, also
> **disable source/destination check** and open the control-plane/worker ports.

## Prep — run on ALL nodes (master + workers)
Before kubeadm runs, every node needs swap off, kernel modules loaded, and the
container runtime ready — otherwise the kubelet won't start.

```bash
# 1. disable swap (kubelet requires it off)
swapoff -a
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

# 3. install containerd, then kubeadm/kubelet/kubectl (pin a version e.g. 1.29)
# 4. point crictl at containerd
sudo crictl config runtime-endpoint unix:///var/run/containerd/containerd.sock
```
> Installing **1.29** on purpose so a later day can practice upgrading to 1.30.

## Initialize the control plane — MASTER only
`kubeadm init` runs only on the master; it stands up the control plane and prints
the join command for workers.

```bash
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --apiserver-advertise-address=<master-private-ip> \
  --node-name master
```
Save the printed `kubeadm join ...` command — workers need it.

Set up kubeconfig for your user:
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Install the CNI (Calico) so pods/nodes go Ready:
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml
kubectl apply -f custom-resources.yaml
```

## Join the workers — WORKER nodes
Run prep steps 1-4 on each worker, then the join command from `kubeadm init`:
```bash
sudo kubeadm join <master-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>

# lost the command? regenerate it on the master:
kubeadm token create --print-join-command
```

## Validate
Confirm every node is **Ready** and the system pods are running before trusting
the cluster.

```bash
kubectl get nodes        # all 3 should be Ready
kubectl get pods -A      # control plane + calico pods Running
```

## Troubleshooting Calico
- Disable source/dest check on every node (AWS).
- Allow **BGP TCP 179** between nodes in the security group.
- If calico-node is unhealthy, pin the autodetect interface:
```bash
kubectl set env daemonset/calico-node -n calico-system \
  IP_AUTODETECTION_METHOD=interface=ens5     # ens5 = your real NIC (ifconfig)
```

## Key takeaways
- `kubeadm init` builds the control plane; `kubeadm join` adds workers.
- **swapoff** + **br_netfilter/ip_forward** are mandatory prep on every node.
- A **CNI (Calico)** must be installed before nodes report Ready.
- Keep the `join` command (or regenerate with `kubeadm token create`).

## Checklist
- [ ] Provisioned 3 VMs and opened the required ports
- [ ] Ran swap/iptables/containerd prep on all nodes
- [ ] `kubeadm init` on master + configured kubeconfig
- [ ] Installed Calico and joined both workers
- [ ] `kubectl get nodes` shows 3 Ready nodes
