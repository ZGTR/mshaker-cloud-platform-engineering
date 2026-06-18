# Day 38 — Troubleshoot Cluster Component Failure

> Video: Day 38/40 — Troubleshoot cluster component failure
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Problem & solution
When the **control plane** or a **node** is sick, `kubectl` may be slow, lying,
or dead — so app-level triage (Day 37) isn't enough. You must drop to the node
and inspect the kubelet, the container runtime, and the static-pod control-plane
components directly.

**Solution:** When kubectl is unreliable, debug on the node with journalctl -u kubelet and crictl against the static-pod control plane.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------------- CLUSTER --------------------------------------+
   | +-------------------------------- CONTROL PLANE ---------------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+                 | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr |                 | |
   | | +------------+   +------+   +-----------+   +----------------+                 | |
   | | api-server  <== control-plane runs as static pods in /etc/kubernetes/manifests | |
   | +--------------------------------------------------------------------------------+ |
   | +--- WORKER NODE   (kubelet | kube-proxy | runtime) ----+                          |
   | |    <== check kubelet + containerd health on each node |                          |
   | | + namespace: default +                                |                          |
   | | | +----- POD -----+  |                                |                          |
   | | | | + CONTAINER + |  |                                |                          |
   | | | | | app       | |  |                                |                          |
   | | | | +-----------+ |  |                                |                          |
   | | | +---------------+  |                                |                          |
   | | +--------------------+                                |                          |
   | +-------------------------------------------------------+                          |
   +------------------------------------------------------------------------------------+
```

## The key insight: control plane = static pods
On a kubeadm cluster the api-server, scheduler, controller-manager, and etcd run
as **static pods** — the kubelet starts them from manifest files on disk, not
from the api-server. So even if the API is down, the kubelet keeps trying to run
them, and you debug them with `crictl`, not `kubectl`.

```
   /etc/kubernetes/manifests/
     kube-apiserver.yaml          kubelet watches this dir and runs each as a pod
     kube-controller-manager.yaml
     kube-scheduler.yaml
     etcd.yaml
   logs (when kubectl can't help): /var/log/containers/, crictl logs, journalctl
```

## End-to-end: a NotReady node
```
   +-----+        +------+        +---------+
   | you |        | node |        | kubelet |
   +-----+        +------+        +---------+
      |               |                |
      | (1) kubectl get nodes -> NotReady (or API down)
      |-------------->|                |
      |               |                |
      | (2) systemctl status kubelet; journalctl -u kubelet
      |------------------------------->|
      |               |                |
     (3) control-plane pods are static: ls /etc/kubernetes/manifests
      |               |                |
     (4) crictl ps / crictl logs for apiserver|etcd|scheduler containers
      |               |                |
   Control-plane components are static pods; the kubelet + containerd run them.
```

## kubelet first (most node problems live here)
```bash
systemctl status kubelet                 # running? failed?
sudo journalctl -u kubelet -f --no-pager # live kubelet logs (cert? cgroup? CNI?)
sudo systemctl restart kubelet           # after fixing config
```
Common kubelet causes: **swap re-enabled**, **cgroup driver mismatch** (must
match containerd's `SystemdCgroup`), **expired certs**, **disk/PID pressure**,
**CNI not ready**.

## Runtime + static pods with crictl (when kubectl is down)
```bash
sudo crictl ps -a                         # all containers, incl. crashed CP ones
sudo crictl logs <container-id>           # logs for apiserver/etcd/etc.
sudo crictl pods                          # pod sandboxes
ls /etc/kubernetes/manifests/             # the static-pod manifests
sudo systemctl status containerd          # runtime healthy?
```

## etcd / api-server health
```bash
# api-server readiness (works even when RBAC for kubectl doesn't)
kubectl get --raw='/readyz?verbose'

# etcd health (certs from Day 35)
sudo ETCDCTL_API=3 etcdctl endpoint health \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

## Symptom -> where to look
```
   kubectl times out / refused      -> api-server static pod (crictl logs); LB; certs
   node NotReady                     -> kubelet (journalctl); CNI; disk/mem pressure
   pods Pending cluster-wide         -> scheduler down (crictl logs kube-scheduler)
   deployments don't scale/heal      -> controller-manager down
   everything flaky / data weird     -> etcd unhealthy or out of quorum
   certs expired                     -> kubeadm certs check-expiration; renew
   manifest typo                     -> CP pod won't start; crictl logs shows parse error
```

## Common pitfalls
```
   - looking in kubectl when the API itself is down  -> use crictl + journalctl
   - swap turned back on after reboot                -> kubelet won't start
   - cgroup driver mismatch                          -> kubelet/containerd disagree
   - editing a static-pod manifest with a typo       -> that component won't come up
   - clock skew between nodes                         -> TLS + etcd raft break
```

## Key takeaways
- The control plane runs as **static pods** from `/etc/kubernetes/manifests`.
- When `kubectl` is dead, debug with **`crictl`** + **`journalctl -u kubelet`**.
- **kubelet** is the usual node culprit: swap, cgroup driver, certs, CNI, pressure.
- Use `/readyz?verbose` for the api-server and `etcdctl endpoint health` for etcd.
- Map the symptom (API/scheduler/controller/etcd) to the component to inspect.

## Checklist
- [ ] Explained why control-plane components are static pods
- [ ] Checked `systemctl status kubelet` and `journalctl -u kubelet`
- [ ] Used `crictl ps`/`crictl logs` to inspect a control-plane container
- [ ] Queried `/readyz?verbose` and `etcdctl endpoint health`
- [ ] Mapped 3+ symptoms to the failing component
