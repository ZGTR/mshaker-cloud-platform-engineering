# Day 34 — Cluster Version Upgrade with kubeadm

> Video: Day 34/40 — Perform a version upgrade on a Kubernetes cluster using kubeadm
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| kubeadm upgrade | Drives the cluster version bump |
| upgrade plan/apply | Preview / perform the upgrade |
| Skew policy | Upgrade one minor version at a time |
| drain/cordon/uncordon | The node maintenance flow |
| apt-mark hold | Pins package versions |
| kubelet | Upgraded per node after the plan applies |

## Problem & solution
Kubernetes ships a new minor release every ~4 months and only supports the last
three. Clusters must be upgraded — safely, with no downtime, and in the right
order. Skipping minors or upgrading nodes before the control plane breaks the
cluster. `kubeadm upgrade` orchestrates this correctly.

**Solution:** Upgrade one minor at a time with kubeadm, control plane first (upgrade apply), then drain, upgrade, and uncordon each worker.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------------- CLUSTER -----------------------------------+
   | +------------------------------ CONTROL PLANE ------------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+            | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr |            | |
   | | +------------+   +------+   +-----------+   +----------------+            | |
   | | api-server  <== kubeadm upgrade: control plane first, one minor at a time | |
   | +---------------------------------------------------------------------------+ |
   | +----- WORKER NODE   (kubelet | kube-proxy | runtime) ------+                 |
   | |    <== drain -> upgrade kubelet -> uncordon, node by node |                 |
   | | + namespace: default +                                    |                 |
   | | | +----- POD -----+  |                                    |                 |
   | | | | + CONTAINER + |  |                                    |                 |
   | | | | | app       | |  |                                    |                 |
   | | | | +-----------+ |  |                                    |                 |
   | | | +---------------+  |                                    |                 |
   | | +--------------------+                                    |                 |
   | +-----------------------------------------------------------+                 |
   +-------------------------------------------------------------------------------+
```

## The golden rules
```
   1. ONE minor at a time:   1.29 -> 1.30 -> 1.31  (never 1.29 -> 1.31)
   2. Control plane FIRST, then workers.
   3. components must stay within ONE minor of the api-server (kubelet skew: -3).
   4. Back up etcd BEFORE you start (see Day 35).
```

## End-to-end: the upgrade flow
```
   +-------+        +---------------+        +--------+
   | admin |        | control-plane |        | worker |
   +-------+        +---------------+        +--------+
       |                    |                     |
       | (1) apt install kubeadm=1.30; kubeadm upgrade apply v1.30.x
       |------------------->|                     |
       |                    |                     |
     (2) then upgrade kubelet + kubectl on the control plane, restart kubelet
       |                    |                     |
       | (3) kubectl drain <worker> (evict pods safely)
       |----------------------------------------->|
       |                    |                     |
     (4) on the worker: apt install kubelet=1.30; kubeadm upgrade node
       |                    |                     |
       | (5) kubectl uncordon <worker> (schedulable again)
       |----------------------------------------->|
       |                    |                     |
   One minor at a time; control plane first, then nodes one-by-one.
```

## Step 1 — first control-plane node
```bash
# unhold + install the new kubeadm only
sudo apt-mark unhold kubeadm
sudo apt-get update && sudo apt-get install -y kubeadm=1.30.2-1.1
sudo apt-mark hold kubeadm

# see the plan, then apply
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply v1.30.2        # upgrades apiserver/scheduler/etc + etcd

# now upgrade this node's kubelet + kubectl, then restart kubelet
sudo apt-mark unhold kubelet kubectl
sudo apt-get install -y kubelet=1.30.2-1.1 kubectl=1.30.2-1.1
sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet
```

## Step 2 — additional control-plane nodes
Same as above but use `kubeadm upgrade node` (not `apply`):
```bash
sudo kubeadm upgrade node        # then upgrade kubelet/kubectl + restart as above
```

## Step 3 — each worker (one at a time)
```bash
# from the control plane: evict workloads safely
kubectl drain <worker> --ignore-daemonsets --delete-emptydir-data

# on the worker: upgrade kubeadm, then the node config, then kubelet
sudo apt-mark unhold kubeadm && sudo apt-get install -y kubeadm=1.30.2-1.1 && sudo apt-mark hold kubeadm
sudo kubeadm upgrade node
sudo apt-mark unhold kubelet kubectl
sudo apt-get install -y kubelet=1.30.2-1.1 kubectl=1.30.2-1.1
sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet

# back on the control plane: allow scheduling again
kubectl uncordon <worker>
```

## Verify
```bash
kubectl version                       # server == target
kubectl get nodes                     # every node VERSION = v1.30.2, all Ready
kubectl get pods -A                    # nothing crashing after the upgrade
```

## drain / cordon / uncordon
```
   cordon    mark node unschedulable (no NEW pods); existing pods stay
   drain     cordon + EVICT existing pods (respecting PodDisruptionBudgets)
   uncordon  mark schedulable again (after the node is upgraded)
```

## Common pitfalls
```
   - skipping a minor              -> unsupported; upgrade one minor at a time
   - upgrading workers first       -> version skew breaks the kubelet/api-server
   - forgetting apt-mark hold      -> an unattended apt upgrade skews versions
   - no etcd backup first          -> a failed upgrade with no rollback path
   - drain hangs                   -> a PodDisruptionBudget blocks eviction; check PDBs
   - kubelet not restarted         -> node still reports the old version
```

## Key takeaways
- Upgrade **one minor at a time**, **control plane before workers**.
- `kubeadm upgrade apply` on the first control-plane node; `upgrade node` elsewhere.
- Per node: install `kubeadm` -> upgrade -> install `kubelet`/`kubectl` -> restart.
- **drain** before, **uncordon** after, for every worker.
- **Back up etcd first** (Day 35); keep versions **held** between upgrades.

## Checklist
- [ ] Backed up etcd before starting
- [ ] Ran `kubeadm upgrade plan` and `apply` on the first control-plane node
- [ ] Upgraded kubelet/kubectl and restarted the kubelet on each control-plane node
- [ ] Drained, upgraded, and uncordoned each worker one at a time
- [ ] Verified every node shows the target version and is Ready
