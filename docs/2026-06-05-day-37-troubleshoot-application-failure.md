# Day 37 — Troubleshoot Application Failure

> Video: Day 37/40 — Troubleshoot application failure
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Key terms
| Term | Meaning |
| --- | --- |
| CrashLoopBackOff | Container keeps crashing and restarting |
| Pending | Pod cannot be scheduled |
| ImagePullBackOff | Image cannot be pulled |
| describe | Shows an object's events and reasons |
| logs / --previous | Current / last container logs |
| Endpoints | The pod IPs behind a Service |
| Readiness | 0/1 Ready means the readiness probe is failing |

## Problem & solution
Most "Kubernetes is broken" tickets are actually one app misbehaving:
a bad image tag, a missing env var, a failing probe, or too little memory. You
need a fast, repeatable triage path that finds the cause without guessing.

**Solution:** Triage in order, get then describe (Events) then logs --previous, and map the status string (ImagePullBackOff/CrashLoop/OOMKilled/Pending) to its cause.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +------------------------------ CLUSTER -------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+   |
   | | +------------+   +------+   +-----------+   +----------------+ |   |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |   |
   | | +------------+   +------+   +-----------+   +----------------+ |   |
   | +----------------------------------------------------------------+   |
   | +--------- WORKER NODE   (kubelet | kube-proxy | runtime) ---------+ |
   | | +--------------------- namespace: default ---------------------+ | |
   | | | +-------------------------- POD ---------------------------+ | | |
   | | | | +--------------------- CONTAINER ----------------------+ | | | |
   | | | | | app                                                  | | | | |
   | | | | |    <== CrashLoopBackOff, ImagePullBackOff, OOMKilled | | | | |
   | | | | +------------------------------------------------------+ | | | |
   | | | |    <== describe / logs / events to diagnose app failures | | | |
   | | | +----------------------------------------------------------+ | | |
   | | +--------------------------------------------------------------+ | |
   | +------------------------------------------------------------------+ |
   +----------------------------------------------------------------------+
```

## The triage path (memorize this order)
```
   +-----+        +---------+        +-----+
   | you |        | kubectl |        | pod |
   +-----+        +---------+        +-----+
      |                |                |
      | (1) kubectl get pods -> CrashLoopBackOff
      |--------------->|                |
      |                |                |
      |                | (2) kubectl describe pod -> Events (image? OOM? probe?)
      |                |--------------->|
      |                |                |
      |                | (3) kubectl logs --previous -> the crash reason
      |                |--------------->|
      |                |                |
     (4) fix: image tag / env / resources / probe; re-apply
      |                |                |
   Order: get -> describe (events) -> logs --previous. Most answers are there.
```

## The commands
```bash
kubectl get pods -o wide                 # status, restarts, node, age
kubectl describe pod <pod>               # Events at the bottom = gold
kubectl logs <pod>                        # current container logs
kubectl logs <pod> --previous            # the CRASHED instance's logs
kubectl get events --sort-by=.lastTimestamp -n <ns>   # recent cluster events
kubectl exec -it <pod> -- sh             # poke inside a running container
kubectl debug -it <pod> --image=busybox --target=<container>   # ephemeral debug
```

## Decode the status
```
   ImagePullBackOff / ErrImagePull  wrong image name/tag, private registry, no pull secret
   CrashLoopBackOff                 container starts then exits repeatedly -> read logs --previous
   OOMKilled (in describe)          hit the memory LIMIT -> raise limit or fix the leak (Day 16)
   CreateContainerConfigError       missing ConfigMap/Secret referenced by the pod
   Pending                          can't schedule: no resources / taints / PVC unbound (Day 16/14/29)
   RunContainerError                bad command/entrypoint or volume mount
   0/1 Ready (Running)              readiness probe failing -> not in Service endpoints
```

## Worked examples
```bash
# CrashLoopBackOff: read why it died, not why it's restarting
kubectl logs <pod> --previous
kubectl describe pod <pod> | sed -n '/Events/,$p'

# Pending: why won't it schedule?
kubectl describe pod <pod> | grep -A5 Events     # "Insufficient cpu" / "had taint" / "unbound PVC"

# 0/1 Ready but Running: readiness probe
kubectl describe pod <pod> | grep -A3 Readiness
kubectl get endpointslices -l kubernetes.io/service-name=<svc>   # is the pod a target?

# Service returns nothing: are there endpoints at all?
kubectl get endpoints <svc>      # empty = no ready pods behind it
```

## A mental decision tree
```
   pod not RUNNING?
     Pending           -> describe -> scheduling reason (cpu/taint/PVC)
     ImagePull*        -> fix image name/tag or add imagePullSecret
     Config error      -> the referenced ConfigMap/Secret is missing
   pod RUNNING but bad?
     restarts climbing -> logs --previous (crash) ; describe (OOMKilled?)
     0/1 Ready         -> readiness probe / app not listening on the port
   pod READY but no traffic?
     Service           -> selector matches labels? endpoints non-empty?
     DNS / NetworkPolicy / wrong port  (Day 31 / Day 26)
```

## Common pitfalls
```
   - reading current logs for a crashed pod  -> use --previous
   - editing a pod directly                  -> edit the Deployment; pods are cattle
   - ignoring the Events section             -> it usually states the exact cause
   - "it works on my machine"               -> check the ConfigMap/Secret/env in-cluster
```

## Key takeaways
- Triage order: **get -> describe (Events) -> logs --previous**.
- The **status string** (ImagePullBackOff/CrashLoop/OOMKilled/Pending) names the class of bug.
- **Pending** = scheduling; **CrashLoop** = app exits; **0/1 Ready** = readiness probe.
- No traffic? Check the **Service selector + endpoints**, then DNS/NetworkPolicy.
- Fix the **controller** (Deployment), not the individual pod.

## Checklist
- [ ] Can recite the get -> describe -> logs --previous order
- [ ] Mapped each status string to its likely cause
- [ ] Used `kubectl logs --previous` on a CrashLoop pod
- [ ] Diagnosed a Pending pod from describe Events
- [ ] Checked Service endpoints when traffic didn't flow
