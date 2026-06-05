# Day 12 — DaemonSet, Job & CronJob

> Video: Day 12/40 — Kubernetes Daemonset Explained — Daemonsets, Job and Cronjob
> https://www.youtube.com/watch?v=kvITrySpy_k
> Duration: ~28 min

## Three special workload controllers

```
   DaemonSet  -> one pod on EVERY node           (agents)
   Job        -> run to completion, then stop     (batch task)
   CronJob    -> Job on a schedule                (cron)
```

## DaemonSet — one pod per node

```
   +--- node1 ---+  +--- node2 ---+  +--- node3 ---+
   | [ds-pod]    |  | [ds-pod]    |  | [ds-pod]    |
   +-------------+  +-------------+  +-------------+
   New node joins -> DaemonSet auto-adds a pod there.
```
Use for **node-level agents**: log collectors (fluentd), monitoring
(node-exporter), CNI plugins, kube-proxy.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-agent
spec:
  selector:
    matchLabels: { app: agent }
  template:
    metadata:
      labels: { app: agent }
    spec:
      containers:
        - name: agent
          image: busybox
          command: ['sh','-c','while true; do sleep 3600; done']
```

## Job — run once to completion

```
   [pod] --runs task--> Completed (exit 0)
   - Not restarted on success.
   - Retries on failure up to backoffLimit.
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 1          # how many successful pods needed
  parallelism: 1          # how many run at once
  backoffLimit: 4         # retries before marking failed
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: pi
          image: perl
          command: ['perl','-Mbignum=bpi','-wle','print bpi(200)']
```

## CronJob — Jobs on a schedule

```
   schedule: "*/5 * * * *"   (every 5 min)
      |   |   |   |   |
      |   |   |   |   +-- day of week (0-6)
      |   |   |   +------ month (1-12)
      |   |   +---------- day of month (1-31)
      |   +-------------- hour (0-23)
      +------------------ minute (0-59)

   tick -> creates a Job -> creates a Pod -> runs -> done
```

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"        # daily at 02:00
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: busybox
              command: ['sh','-c','echo backing up...']
```

## Commands
```bash
kubectl get daemonset -A
kubectl get jobs
kubectl get cronjobs
kubectl logs job/pi
kubectl create job manual --from=cronjob/backup    # trigger now
```

## When to use which
```
   Need it on every node?           -> DaemonSet
   One-off batch task?              -> Job
   Recurring scheduled task?        -> CronJob
   Long-running stateless service?  -> Deployment (Day 8)
```

## Key takeaways
- **DaemonSet** = exactly one pod per (matching) node, auto-scales with nodes.
- **Job** runs to completion (`completions`, `parallelism`, `backoffLimit`).
- **CronJob** spawns Jobs on a cron `schedule`.

## Checklist
- [ ] Deployed a DaemonSet and saw one pod per node
- [ ] Ran a Job to completion and read its logs
- [ ] Created a CronJob and manually triggered it with `--from`
