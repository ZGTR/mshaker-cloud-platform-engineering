# Day 9 — Kubernetes Services: ClusterIP vs NodePort vs LoadBalancer vs ExternalName

> Video: Day 9/40 — Kubernetes Services Explained
> https://www.youtube.com/watch?v=tHAQWLKMTB0
> Duration: ~46 min

## Why Services exist
Pods are **ephemeral** — they die and get recreated with **new IPs**. You can't
rely on a pod IP. A **Service** gives a **stable virtual IP + DNS name** and
load-balances across the matching pods.

```
   Without Service: client -> pod IP (changes! breaks)
   With Service:    client -> Service (stable) -> [pod][pod][pod]
```

## How a Service finds its pods: labels & selectors

```
   Service.spec.selector: app=web
                 |
                 v   matches
   [pod app=web] [pod app=web] [pod app=web]
   (Service builds an Endpoints list of matching pod IPs)
```

```bash
kubectl get endpoints <svc>     # the actual pod IPs behind a service
```

## The 4 Service types

### 1) ClusterIP (default) — internal only
```
   +------------------ cluster ------------------+
   | clientPod -> [ClusterIP svc] -> [pod][pod]  |
   |   reachable ONLY inside the cluster         |
   +---------------------------------------------+
```
Use for pod-to-pod / internal microservice traffic.

### 2) NodePort — expose on every node's IP at a high port
```
   user -> NodeIP:30007 -> [NodePort svc] -> [pod][pod]
                       (port range 30000-32767)
   Every node forwards that port, even nodes without the pod.
```

### 3) LoadBalancer — cloud external LB
```
   internet -> Cloud LB (public IP) -> NodePort -> ClusterIP -> pods
   (provisioned by the cloud provider; AWS/GCP/Azure)
```

### 4) ExternalName — DNS alias to an external host
```
   pod -> svc(my-db) --CNAME--> db.example.com
   No proxying; just a DNS CNAME record. No selector/pods.
```

## Layering (each type builds on the previous)
```
   LoadBalancer
       wraps  NodePort
                  wraps  ClusterIP  ----> Pods
```

## Service YAML examples
ClusterIP:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
    - port: 80          # service port
      targetPort: 80    # container port
```

NodePort:
```yaml
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30007   # optional; auto-assigned if omitted
```

## port vs targetPort vs nodePort
```
   nodePort (30007)  -> on each Node's IP        (external entry, NodePort/LB)
   port (80)         -> on the Service's ClusterIP (in-cluster entry)
   targetPort (80)   -> on the Pod/container       (final destination)
```

## Commands
```bash
kubectl expose deployment web --port=80 --target-port=80 --type=NodePort
kubectl get svc
kubectl get svc web -o wide
kubectl describe svc web

# test internal DNS from another pod
kubectl run tmp --image=busybox -it --rm -- wget -qO- web:80
```

## Service DNS name
```
   <service>.<namespace>.svc.cluster.local
   e.g.  web.default.svc.cluster.local
```

## Key takeaways
- Services give a **stable IP/DNS + load balancing** over ephemeral pods.
- **ClusterIP** internal, **NodePort** node IPs, **LoadBalancer** cloud public,
  **ExternalName** DNS alias.
- Remember the **port / targetPort / nodePort** trio.

## Checklist
- [ ] Exposed a Deployment as ClusterIP and reached it from another pod
- [ ] Created a NodePort and hit it on a node IP
- [ ] Inspected `kubectl get endpoints`
- [ ] Can explain port vs targetPort vs nodePort
