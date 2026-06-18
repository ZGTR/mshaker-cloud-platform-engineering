# Day 5 — What is Kubernetes? Architecture Explained

> Video: Day 5/40 — What is Kubernetes — Kubernetes Architecture Explained
> https://www.youtube.com/watch?v=SGGkUCctL4I
> Duration: ~25 min

## Problem & solution
To operate or troubleshoot Kubernetes you must know which component does what.
Treating the cluster as a black box makes failures impossible to reason about,
so we first map the control plane and worker node pieces and how they interact.

**Solution:** Split work into a control plane (api-server, etcd, scheduler, controller-manager) that decides desired state and worker nodes (kubelet, kube-proxy, runtime) that run it.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== front door: everything talks here              | |
   | | etcd  <== key-value store of ALL cluster state                 | |
   | | scheduler  <== assigns pods to nodes                           | |
   | | controller-mgr  <== drives actual state -> desired state       | |
   | +----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                 |
   | |    <== runs the actual workloads               |                 |
   | | +-------- namespace: default ---------+        |                 |
   | | | +-------------- POD --------------+ |        |                 |
   | | | | +------ CONTAINER ------+       | |        |                 |
   | | | | | app                   |       | |        |                 |
   | | | | |    <== your app image |       | |        |                 |
   | | | | +-----------------------+       | |        |                 |
   | | | |    <== smallest deployable unit | |        |                 |
   | | | +---------------------------------+ |        |                 |
   | | +-------------------------------------+        |                 |
   | +------------------------------------------------+                 |
   +--------------------------------------------------------------------+
```

## Cluster = Control Plane + Worker Nodes
A cluster splits into a **control plane** that makes decisions and **worker
nodes** that run the actual workloads.

```
  +=================== KUBERNETES CLUSTER ===================+
  |                                                          |
  |   CONTROL PLANE (the brain)                              |
  |   +--------------------------------------------------+   |
  |   | kube-apiserver   <--- front door (all talk here) |   |
  |   |     |                                            |   |
  |   |   etcd           <--- key-value store (state)    |   |
  |   | scheduler        <--- picks node for new pods    |   |
  |   | controller-mgr   <--- runs control loops         |   |
  |   | cloud-controller <--- talks to cloud provider    |   |
  |   +--------------------------------------------------+   |
  |              ^                                           |
  |              | (kubectl / API)                           |
  |              v                                           |
  |   WORKER NODES (the muscle)                              |
  |   +---------------------+   +---------------------+      |
  |   | kubelet             |   | kubelet             |      |
  |   | kube-proxy          |   | kube-proxy          |      |
  |   | container runtime   |   | container runtime   |      |
  |   |  [pod][pod][pod]    |   |  [pod][pod]         |      |
  |   +---------------------+   +---------------------+      |
  +==========================================================+
```

## Control Plane components
The **control plane** is the cluster's brain — these components decide what
should run and where.

| Component | Role |
|-----------|------|
| **kube-apiserver** | The only entry point. Validates & serves the K8s API. Everything goes through it. |
| **etcd** | Consistent key-value DB. Stores the entire cluster state ("source of truth"). |
| **kube-scheduler** | Watches for unscheduled pods, picks the best node (resources, taints, affinity). |
| **kube-controller-manager** | Runs controllers (node, replication, endpoints...) that drive desired state. |
| **cloud-controller-manager** | Integrates with cloud APIs (load balancers, volumes, nodes). |

## Worker Node components
Each **worker node** runs these agents to host pods and wire up their
networking.

| Component | Role |
|-----------|------|
| **kubelet** | Agent on each node. Talks to API server, ensures pod containers are running/healthy. |
| **kube-proxy** | Maintains network rules so Services route traffic to the right pods. |
| **container runtime** | Actually runs containers (containerd / CRI-O). |

## How a pod gets created (request flow)
Creating a pod is a relay: the request flows through the **API server**, gets
stored, scheduled, then run on a node.

```
  kubectl apply -f pod.yaml
        |
        v
  [1] kube-apiserver  --validate--> [2] etcd (store desired state)
        |
        v
  [3] scheduler picks a node, writes binding back to apiserver
        |
        v
  [4] kubelet on chosen node sees the assignment
        |
        v
  [5] container runtime pulls image + starts container
        |
        v
  [6] kubelet reports status -> apiserver -> etcd (actual state)
```

## Mental model
A quick analogy for who does what across the control plane and each node.

```
   etcd     = the database (what SHOULD exist)
   apiserver= the receptionist (all requests pass through)
   scheduler= the planner (where things go)
   controllers = the workers (keep reality == desired)
   kubelet  = the foreman on each node (make it so locally)
```

## Key takeaways
- **All communication flows through the API server.**
- **etcd** is the single source of truth — back it up (covered Day 35).
- Scheduler decides placement; kubelet executes on the node.

## Checklist
- [ ] Can name all control-plane and node components and their jobs
- [ ] Can trace the pod-creation request flow end to end
