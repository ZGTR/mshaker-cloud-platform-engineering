# Day 39 — Network Troubleshooting & Node Maintenance

> Video: Day 39/40 — Network Troubleshooting
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| cordon | Mark a node unschedulable |
| drain | Evict pods for maintenance |
| uncordon | Re-enable scheduling on a node |
| DNS/Service/pod layers | Debug networking top-down |
| Endpoints | The pod IPs behind a Service |
| netshoot | Throwaway pod with network tools |
| kube-proxy / CNI | The networking data path |

## Problem & solution
Networking failures are the hardest to debug because the request crosses many
layers: DNS, the Service VIP, kube-proxy, the CNI, and NetworkPolicies. You need
a layered method to find *where* a connection dies. This day also covers safely
taking a node out for maintenance (cordon/drain) and bringing it back.

**Solution:** Debug layer by layer (DNS, Service/endpoints, kube-proxy, CNI, policy, firewall), and cordon/drain/uncordon nodes for safe maintenance.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------- CLUSTER --------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |     |
   | | +------------+   +------+   +-----------+   +----------------+ |     |
   | +----------------------------------------------------------------+     |
   | +---------- WORKER NODE   (kubelet | kube-proxy | runtime) ----------+ |
   | |    <== cordon/drain for maintenance; check CNI + kube-proxy        | |
   | | +---------------------- namespace: default ----------------------+ | |
   | | | +----- POD -----+                                              | | |
   | | | | + CONTAINER + |                                              | | |
   | | | | | app       | |                                              | | |
   | | | | +-----------+ |                                              | | |
   | | | +---------------+                                              | | |
   | | |    <== Service / DNS / NetworkPolicy are common failure points | | |
   | | +----------------------------------------------------------------+ | |
   | +--------------------------------------------------------------------+ |
   +------------------------------------------------------------------------+
```

## Debug by layer (top to bottom)
Walk the path a request takes and test each hop in order:

```
   1. DNS       does the name resolve?        nslookup <svc> from a pod (Day 31)
   2. Service   is there a ClusterIP + endpoints?   kubectl get svc,endpoints <svc>
   3. kube-proxy are the rules present?        iptables-save | grep <clusterip>
   4. CNI / pod can pods reach pods directly?  curl <pod-ip>:<port> from a debug pod
   5. policy    is a NetworkPolicy dropping it? kubectl get netpol; test allow/deny
   6. node/fw   is a node/cloud firewall blocking the port?
```

## The toolkit
```bash
# a throwaway pod with network tools
kubectl run net --image=nicolaka/netshoot -it --rm -- bash
  # inside: nslookup, dig, curl, ping, traceroute, ss, iptables, tcpdump

kubectl get svc,endpoints <svc> -o wide      # VIP + the pods behind it (empty = no ready pods)
kubectl get pods -o wide                      # pod IPs and nodes
kubectl get networkpolicy -A                  # policies that might be dropping traffic
kubectl exec <pod> -- curl -sS <other-svc>:<port>   # test app-to-app
```

## Decision tree
```
   name won't resolve      -> CoreDNS down / NetworkPolicy blocks 53 / wrong name (Day 31)
   resolves, conn refused  -> no endpoints (no ready pods) OR wrong targetPort
   endpoints exist, no conn -> NetworkPolicy deny / CNI broken between nodes
   works same node, not cross-node -> overlay/BGP firewall (VXLAN 8472 / BGP 179)
   external can't reach     -> Service type / Ingress / cloud SG / nodePort firewall
   intermittent             -> one bad pod behind the Service; check readiness
```

## Node maintenance: cordon / drain / uncordon
To patch or reboot a node safely, stop new pods, evict the running ones, do the
work, then re-enable scheduling.

```bash
kubectl cordon <node>          # mark unschedulable (no NEW pods); running pods stay
kubectl drain <node> \
  --ignore-daemonsets \         # DaemonSet pods can't be evicted; skip them
  --delete-emptydir-data        # allow evicting pods using emptyDir
# ... reboot / patch / upgrade the node ...
kubectl uncordon <node>        # mark schedulable again
```
```
   cordon    no new pods land here (existing ones keep running)
   drain     cordon + evict existing pods elsewhere (respects PodDisruptionBudgets)
   uncordon  undo cordon; the node accepts pods again
```
> A **PodDisruptionBudget** can block a drain to protect availability — that's
> by design. Check `kubectl get pdb -A` if a drain hangs.

## Common pitfalls
```
   - Service has no endpoints       -> selector doesn't match pod labels, or pods not Ready
   - targetPort != containerPort    -> Service points at the wrong port
   - NetworkPolicy default-deny      -> forgot to allow DNS (53) or the needed peer
   - cross-node fails only           -> firewall blocks the CNI transport
   - drain hangs forever             -> a restrictive PDB or un-evictable pod
   - forgot to uncordon              -> node stays empty after maintenance
```

## Key takeaways
- Debug networking **layer by layer**: DNS -> Service/endpoints -> kube-proxy -> CNI -> policy -> firewall.
- **No endpoints** behind a Service is the most common cause — check labels + readiness.
- **Cross-node only** failures point at the CNI transport / node firewall.
- `netshoot` gives you every tool in a pod; `kubectl get svc,endpoints` is step one.
- Maintenance = **cordon -> drain -> work -> uncordon**; mind **PodDisruptionBudgets**.

## Checklist
- [ ] Can list the layers to test in order (DNS -> Service -> proxy -> CNI -> policy)
- [ ] Used a `netshoot` pod to curl/dig/trace inside the cluster
- [ ] Checked `kubectl get svc,endpoints` for an empty endpoint list
- [ ] Identified a NetworkPolicy or cross-node firewall as a blocker
- [ ] Drained and uncordoned a node, and checked PDBs when a drain stalled
