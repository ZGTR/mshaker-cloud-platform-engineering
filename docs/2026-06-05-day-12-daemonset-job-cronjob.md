# Day 12 — DaemonSet, Job & CronJob

> Video: Day 12/40 — Kubernetes Daemonset Explained — Daemonsets, Job and Cronjob
> https://www.youtube.com/watch?v=kvITrySpy_k
> Duration: ~28 min

## Key terms
| Term | Meaning |
| --- | --- |
| DaemonSet | Runs one pod per (matching) node |
| Job | Runs pods until successful completion |
| CronJob | Creates Jobs on a schedule |
| completions/parallelism | How many / how concurrently a Job runs |
| concurrencyPolicy | Whether CronJob runs may overlap |
| Schedule | Cron expression driving a CronJob |

## Problem & solution
Deployments assume long-running, horizontally scalable services, but some
workloads don't fit: an agent that must run on every node, a one-off batch task
that should finish and stop, or a recurring scheduled job.

**Solution:** Pick the right controller for the lifecycle: DaemonSet (one pod per node), Job (run to completion), CronJob (scheduled).

## Where this fits in the cluster
These are **controllers** that live in the control plane and decide *which pods
land on which nodes*. DaemonSet works at the **node** layer, Job/CronJob at the
**pod** layer.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | controller-mgr  <== DaemonSet / Job / CronJob controllers      | |
   | +----------------------------------------------------------------+ |
   | +-- WORKER NODE   (kubelet | kube-proxy | runtime) ---+            |
   | |    <== DaemonSet = exactly one pod per node         |            |
   | | +-------------- namespace: default ---------------+ |            |
   | | | +-------------------- POD --------------------+ | |            |
   | | | | + CONTAINER +                               | | |            |
   | | | | | app       |                               | | |            |
   | | | | +-----------+                               | | |            |
   | | | |    <== Job / CronJob pods run to completion | | |            |
   | | | +---------------------------------------------+ | |            |
   | | +-------------------------------------------------+ |            |
   | +-----------------------------------------------------+            |
   +--------------------------------------------------------------------+
```

## Three special workload controllers
Beyond Deployments, Kubernetes ships **controllers for non-standard workloads**:
node agents, one-off batch tasks, and scheduled tasks.

```
   DaemonSet  -> one pod on EVERY node           (agents)
   Job        -> run to completion, then stop     (batch task)
   CronJob    -> Job on a schedule                (cron)
```

### Where they sit in the controller family
Every controller manages pods, but each answers a different question: *how
many, where, and for how long?*

```
   CONTROLLER     "how many / where"            "how long does a pod live"
   -----------    --------------------------     --------------------------
   Deployment     N replicas, scheduler picks    forever (restarted on exit)
   DaemonSet      exactly 1 per matching node     forever (restarted on exit)
   Job            N completions, anywhere         until task succeeds, then stop
   CronJob        spawns a Job each tick          each Job stops when done
```

> Rule of thumb: **long-running = Deployment/DaemonSet**, **runs-then-exits =
> Job/CronJob**. The restart expectation is the key difference.

## DaemonSet — one pod per node
A **DaemonSet** guarantees a copy of a pod runs on every (matching) node, and
automatically places one on any new node that joins the cluster.

```
   +--- node1 ---+  +--- node2 ---+  +--- node3 ---+
   | [ds-pod]    |  | [ds-pod]    |  | [ds-pod]    |
   +-------------+  +-------------+  +-------------+
   New node joins -> DaemonSet auto-adds a pod there.
```
Use for **node-level agents**: log collectors (fluentd), monitoring
(node-exporter), CNI plugins, kube-proxy.

### DaemonSet vs Deployment scaling
A Deployment's count is something **you choose**; a DaemonSet's count is
**dictated by the cluster size**. You never set `replicas` on a DaemonSet.

```
   Deployment(replicas: 2)         DaemonSet (no replicas field)
   +----+ +----+ +----+            +----+ +----+ +----+
   |node| |node| |node|            |node| |node| |node|
   | P  | | P  | |    |  <- gaps     | P  | | P  | | P  |  <- always full
   +----+ +----+ +----+            +----+ +----+ +----+
   you pick the number             one-per-node, cluster picks the number
```

### Targeting a subset of nodes
Pair a `nodeSelector` (Day 15) or taints/tolerations (Day 14) with a DaemonSet
to run the agent only where it belongs (e.g. only GPU nodes).

```
   nodeSelector: { gpu: "true" }
   +--- gpu node ---+  +--- cpu node ---+  +--- gpu node ---+
   | [ds-pod]       |  |  (skipped)     |  | [ds-pod]       |
   +----------------+  +----------------+  +----------------+
```

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
A **Job** runs a pod until its task finishes successfully, then stops — unlike a
Deployment, it is not meant to stay running.

```
   [pod] --runs task--> Completed (exit 0)
   - Not restarted on success.
   - Retries on failure up to backoffLimit.
```

### completions x parallelism
These two knobs control batch shape: how many successes you need, and how many
pods run at once toward that goal.

```
   completions: 4, parallelism: 2   -> 4 total successes, 2 at a time
   TIME ->
     [pod1][pod3]        (wave 1: two run in parallel)
     [pod2][pod4]        (wave 2: next two after the first finish)
   Done when 4 pods have exited 0.

   completions: 1, parallelism: 1   -> a single one-shot task (the default)
```

### backoffLimit and retries
On failure a Job retries with **exponential backoff** until `backoffLimit` is
hit, then it's marked `Failed` and stops trying.

```
   FAIL -> wait 10s -> FAIL -> wait 20s -> FAIL -> ... -> backoffLimit reached
                                                          -> Job = Failed
   activeDeadlineSeconds: hard cap on total runtime regardless of retries
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
A **CronJob** creates a Job automatically on a recurring cron schedule — the
Kubernetes equivalent of a crontab entry.

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
  schedule: "0 2 * * *"            # daily at 02:00
  concurrencyPolicy: Forbid        # don't start a new run if one is still going
  startingDeadlineSeconds: 120     # skip a missed run if >2 min late
  successfulJobsHistoryLimit: 3    # keep last 3 successful Jobs
  failedJobsHistoryLimit: 1        # keep last 1 failed Job
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

### concurrencyPolicy — what if a run overlaps?
If a Job is still running when the next tick fires, this policy decides what
happens. Critical for long backups or jobs that must not double-run.

```
   Allow   (default): start the new run anyway -> two Jobs run at once
   Forbid           : skip the new run while the old one is still going
   Replace          : kill the old run, start the new one
```

### Object chain: CronJob -> Job -> Pod
A CronJob doesn't run containers directly — it creates **Jobs**, which create
**Pods**. History limits control how many old Jobs are kept around.

```
   CronJob "backup"
      |  tick (02:00)
      v
   Job  backup-28•••••   --creates-->  Pod backup-28•••••-xxxxx
      |  tick (next day)
      v
   Job  backup-28•••••   --creates-->  Pod backup-28•••••-yyyyy
   (old Jobs pruned per successfulJobsHistoryLimit / failedJobsHistoryLimit)
```

## Commands
Everyday commands for inspecting and triggering these controllers.

```bash
kubectl get daemonset -A
kubectl get jobs
kubectl get cronjobs                               # shows SCHEDULE, LAST SCHEDULE
kubectl logs job/pi                                # logs from a Job's pod
kubectl create job manual --from=cronjob/backup    # trigger a CronJob now
kubectl get pods --selector=job-name=pi            # find a Job's pods
kubectl delete job pi                              # also deletes its pods
```

### Reading the STATUS / COMPLETIONS columns
The list output tells you batch progress at a glance.

```
   $ kubectl get jobs
   NAME   COMPLETIONS   DURATION   AGE
   pi     1/1           5s         1m      <- done: 1 of 1 succeeded
   etl    2/4           30s        30s     <- in progress: 2 of 4 done

   $ kubectl get pods
   pi-xxxxx   0/1   Completed   0   1m      <- batch pods end "Completed", not Running
```

## When to use which
A quick decision guide for picking the right controller for the job.

```
   Need it on every node?           -> DaemonSet
   One-off batch task?              -> Job
   Recurring scheduled task?        -> CronJob
   Long-running stateless service?  -> Deployment (Day 8)
```

## End-to-end example: nightly DB backup
A realistic pipeline: a **DaemonSet** log agent on every node, plus a **CronJob**
that backs up a database every night and a way to trigger it on demand.

```
   CronJob "db-backup"  --02:00 tick-->  Job db-backup-2810xx  -->  Pod (runs pg_dump)
                        --next night-->  Job db-backup-2811xx  -->  Pod
   DaemonSet "log-agent" -> one pod on every node, always running
```

```yaml
# 1) node-level agent on EVERY node
apiVersion: apps/v1
kind: DaemonSet
metadata: { name: log-agent }
spec:
  selector: { matchLabels: { app: log-agent } }
  template:
    metadata: { labels: { app: log-agent } }
    spec:
      containers:
        - name: agent
          image: busybox
          command: ['sh','-c','while true; do echo collecting; sleep 30; done']
---
# 2) scheduled backup that must not overlap
apiVersion: batch/v1
kind: CronJob
metadata: { name: db-backup }
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 600
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: postgres:16
              command: ['sh','-c','pg_dump "$DB_URL" > /tmp/dump.sql && echo done']
              env:
                - name: DB_URL
                  value: postgres://user:pass@db:5432/app
```

```bash
kubectl apply -f backup.yaml
kubectl get daemonset log-agent -o wide        # one pod per node
kubectl get cronjob db-backup                  # SCHEDULE + LAST SCHEDULE
kubectl create job test-now --from=cronjob/db-backup   # trigger immediately
kubectl logs job/test-now                      # watch the backup run to Completed
```

## Common pitfalls
The mistakes that surprise people first.

```
   * restartPolicy: Always on a Job  -> rejected; Jobs need Never or OnFailure
   * Pod stuck Completed, not Running -> that's correct for Jobs; don't "fix" it
   * CronJob never fires              -> check timezone, schedule syntax, and
                                         startingDeadlineSeconds skipping runs
   * Overlapping CronJob runs         -> set concurrencyPolicy: Forbid/Replace
   * DaemonSet skips a node           -> node has a taint; add a toleration (Day 14)
   * Job retries forever             -> set backoffLimit + activeDeadlineSeconds
```

## Key takeaways
- **DaemonSet** = exactly one pod per (matching) node, auto-scales with nodes;
  no `replicas` field.
- **Job** runs to completion (`completions`, `parallelism`, `backoffLimit`);
  use `restartPolicy: Never` or `OnFailure`.
- **CronJob** spawns Jobs on a cron `schedule`; control overlap with
  `concurrencyPolicy` and clutter with history limits.
- Batch pods end as **Completed**, not Running — that's expected.

## Checklist
- [ ] Deployed a DaemonSet and saw one pod per node
- [ ] Scoped a DaemonSet to a subset of nodes with a nodeSelector
- [ ] Ran a Job to completion and read its logs
- [ ] Tuned a Job with `completions` + `parallelism`
- [ ] Created a CronJob and manually triggered it with `--from`
- [ ] Set a `concurrencyPolicy` and watched history limits prune old Jobs
