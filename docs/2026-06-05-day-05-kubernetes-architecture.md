# Day 5 — What is Kubernetes? Architecture Explained

> Video: Day 5/40 — What is Kubernetes — Kubernetes Architecture Explained
> https://www.youtube.com/watch?v=SGGkUCctL4I
> Duration: ~25 min

## Cluster = Control Plane + Worker Nodes

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
| Component | Role |
|-----------|------|
| **kube-apiserver** | The only entry point. Validates & serves the K8s API. Everything goes through it. |
| **etcd** | Consistent key-value DB. Stores the entire cluster state ("source of truth"). |
| **kube-scheduler** | Watches for unscheduled pods, picks the best node (resources, taints, affinity). |
| **kube-controller-manager** | Runs controllers (node, replication, endpoints...) that drive desired state. |
| **cloud-controller-manager** | Integrates with cloud APIs (load balancers, volumes, nodes). |

## Worker Node components
| Component | Role |
|-----------|------|
| **kubelet** | Agent on each node. Talks to API server, ensures pod containers are running/healthy. |
| **kube-proxy** | Maintains network rules so Services route traffic to the right pods. |
| **container runtime** | Actually runs containers (containerd / CRI-O). |

## How a pod gets created (request flow)

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
