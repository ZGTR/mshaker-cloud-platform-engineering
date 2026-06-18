# Day 32 — Kubernetes Networking (CNI & Container Runtimes)

> Video: Day 32/40 — Kubernetes Networking
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| CNI | Container Network Interface plugin |
| Pod network | Flat IP space across all nodes |
| kube-proxy | Programs Service routing (iptables/IPVS) |
| CRI | Container Runtime Interface |
| containerd / runc | The runtime / the low-level container launcher |
| Overlay network | Virtual network spanning nodes |
| ContainerCreating | Pod state often blocked on the CNI |

## Problem & solution
Kubernetes makes a hard promise: **every pod gets its own IP and any pod can
reach any other pod without NAT**. Kubernetes itself does not implement that —
it delegates to a **CNI plugin**. Understanding the runtime (containerd/runc) and
the CNI is what lets you debug "pod stuck in ContainerCreating" or "pods can't
talk across nodes".

**Solution:** Let a CNI plugin give every pod a routable IP (no NAT) and kube-proxy turn Service VIPs into load-balanced pod delivery, on top of containerd/runc.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | +----------------------------------------------------------------+ |
   | +------ WORKER NODE   (kubelet | kube-proxy | runtime) -------+    |
   | |    <== the CNI plugin wires every pod's network namespace   |    |
   | | +------------------ namespace: default -------------------+ |    |
   | | | +------------------------ POD ------------------------+ | |    |
   | | | | +------------------- CONTAINER -------------------+ | | |    |
   | | | | | app                                             | | | |    |
   | | | | |    <== each pod gets its own IP in the pod CIDR | | | |    |
   | | | | +-------------------------------------------------+ | | |    |
   | | | +-----------------------------------------------------+ | |    |
   | | +---------------------------------------------------------+ |    |
   | +-------------------------------------------------------------+    |
   +--------------------------------------------------------------------+
```

## The container runtime stack
The kubelet does not run containers directly; it speaks the **CRI** to a
high-level runtime, which calls a low-level OCI runtime.

```
   kubelet --CRI--> containerd ----> runc ----> Linux namespaces + cgroups
   (node agent)     (image pull,     (spawns the   (the actual isolated
                     lifecycle)       process)        process)
```
- **containerd**: pulls images, manages container/snapshot lifecycle (the CRI runtime).
- **runc**: the OCI binary that actually `clone()`s the process with namespaces.
- Docker is **not** required on nodes; Kubernetes removed `dockershim` in 1.24.

## The 4 networking problems Kubernetes solves
```
   1. container <-> container in a pod   -> same network namespace (localhost)
   2. pod <-> pod (same or other node)   -> the CNI plugin (flat, no NAT)
   3. pod <-> Service                     -> kube-proxy (ClusterIP -> pod)
   4. external -> Service                 -> NodePort / LoadBalancer / Ingress
```

## What the CNI does
When the kubelet creates a pod, it calls the **CNI plugin** to set up the pod's
network namespace: allocate an IP from the node's slice of the **pod CIDR**,
create a veth pair into the pod, and program routes so packets reach pods on
other nodes.

```
   pod sandbox created
        |
   kubelet -> CNI ADD:
        - assign IP from pod CIDR (e.g. 192.168.4.7)
        - create veth: pod eth0 <-> node bridge/route
        - program inter-node routes (BGP/VXLAN/overlay or cloud routes)
        |
   pod now has an IP reachable cluster-wide
```
Popular CNIs: **Calico** (BGP/eBPF, NetworkPolicy), **Cilium** (eBPF), **Flannel**
(simple overlay), **Weave**. Pick **one**; it installs to `/etc/cni/net.d` and
`/opt/cni/bin`.

## kube-proxy: Services to pods
`kube-proxy` runs on every node and turns a Service's stable **ClusterIP** into
load-balanced delivery to ready pod IPs, using iptables or IPVS rules.

```bash
kubectl -n kube-system get ds kube-proxy
kubectl get endpointslices -l kubernetes.io/service-name=my-svc  # the targets
```

## Inspect & debug networking
```bash
# CNI config + plugin binaries on a node
ls /etc/cni/net.d/        # the active CNI config
ls /opt/cni/bin/          # the plugin binaries

# runtime view (no Docker)
sudo crictl ps            # running containers
sudo crictl pods          # pod sandboxes

# pod IPs and which node
kubectl get pods -o wide

# pod stuck ContainerCreating -> almost always CNI:
kubectl describe pod <pod>     # look for "failed to set up sandbox" / CNI errors
```

## Common pitfalls
```
   - No CNI installed         -> nodes NotReady, pods stuck ContainerCreating
   - pod CIDR mismatch        -> CNI config CIDR != kubeadm --pod-network-cidr
   - cross-node traffic fails -> firewall blocks the overlay (VXLAN 8472 / BGP 179)
   - cgroup driver mismatch   -> containerd SystemdCgroup must match the kubelet
   - two CNIs installed       -> conflicting config in /etc/cni/net.d
```

## Key takeaways
- Kubernetes guarantees the model (pod IP, no NAT); the **CNI plugin** implements it.
- Runtime chain: **kubelet -> containerd (CRI) -> runc (OCI)**; no Docker needed.
- Four problems: in-pod (localhost), pod-pod (CNI), pod-Service (kube-proxy), external (Ingress/LB).
- "Stuck ContainerCreating" is almost always a **CNI** problem — `describe` the pod.
- Match the **pod CIDR** and open the CNI's transport ports between nodes.

## Checklist
- [ ] Explained kubelet -> containerd -> runc and why Docker isn't required
- [ ] Listed the 4 networking problems and what solves each
- [ ] Found `/etc/cni/net.d` and `/opt/cni/bin` on a node
- [ ] Used `crictl ps`/`crictl pods` and `kubectl get pods -o wide`
- [ ] Diagnosed a ContainerCreating pod via `kubectl describe`
