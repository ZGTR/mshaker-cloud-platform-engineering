# Day 35 — etcd Backup and Restore

> Video: Day 35/40 — Implement etcd backup and restore
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Problem & solution
**etcd is the cluster.** Every object — Deployments, Secrets, RBAC, the lot —
lives in etcd. Lose it and the cluster is gone, even if the nodes are fine. A
backup you have never restored is not a backup. This is the single most
important Day-2 skill (and a guaranteed CKA exam task).

**Solution:** Take regular etcdctl snapshots stored off-cluster, and rehearse restoring them into a new data dir to recover full cluster state.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | etcd  <== etcdctl snapshot save/restore = the cluster backup   | |
   | +----------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                 |
   | | + namespace: default +                         |                 |
   | | | +----- POD -----+  |                         |                 |
   | | | | + CONTAINER + |  |                         |                 |
   | | | | | app       | |  |                         |                 |
   | | | | +-----------+ |  |                         |                 |
   | | | +---------------+  |                         |                 |
   | | +--------------------+                         |                 |
   | +------------------------------------------------+                 |
   +--------------------------------------------------------------------+
```

## End-to-end: save then restore
```
   +-------+        +------+
   | admin |        | etcd |
   +-------+        +------+
       |                |
       | (1) etcdctl snapshot save backup.db
       |--------------->|
       |                |
     (2) copy backup.db OFF the cluster (S3/GCS, encrypted)
       |                |
     --- disaster: etcd data is lost ---
       |                |
       | (3) etcdctl snapshot restore backup.db --data-dir /var/lib/etcd-new
       |--------------->|
       |                |
     (4) point the etcd static pod at the restored data-dir; restart
       |                |
   etcd IS the cluster state: back it up on a schedule and TEST the restore.
```

## Find etcd's connection details
On a kubeadm cluster, etcd runs as a static pod; its certs are under
`/etc/kubernetes/pki/etcd`. The endpoints + cert paths are in the manifest.

```bash
sudo cat /etc/kubernetes/manifests/etcd.yaml | grep -E 'listen-client-urls|cert-file|key-file|trusted-ca-file'
# typical values:
#   --listen-client-urls=https://127.0.0.1:2379,...
#   --cert-file=/etc/kubernetes/pki/etcd/server.crt
#   --key-file=/etc/kubernetes/pki/etcd/server.key
#   --trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

## Back up (snapshot save)
```bash
sudo ETCDCTL_API=3 etcdctl snapshot save /var/backups/etcd-$(date +%F-%H%M).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# verify the snapshot
sudo ETCDCTL_API=3 etcdctl snapshot status /var/backups/etcd-*.db --write-out=table
```
> Copy the `.db` file **off the node** (object storage, encrypted) and schedule
> it (CronJob/systemd timer). A backup on the same disk that died is useless.

## Restore (snapshot restore)
Restore writes the snapshot to a **new data directory**, then you point etcd at it.

```bash
# 1. restore into a fresh data dir (does NOT touch the live one)
sudo ETCDCTL_API=3 etcdctl snapshot restore /var/backups/etcd-2026-06-05.db \
  --data-dir /var/lib/etcd-restore

# 2. stop the control plane so nothing writes during the swap
#    (move static-pod manifests out so the kubelet stops them)
sudo mv /etc/kubernetes/manifests/*.yaml /tmp/manifests-backup/

# 3. point the etcd static pod at the restored dir
sudo sed -i 's#/var/lib/etcd#/var/lib/etcd-restore#' /tmp/manifests-backup/etcd.yaml
#    (or set hostPath volume to /var/lib/etcd-restore)

# 4. put the manifests back; the kubelet restarts etcd + control plane
sudo mv /tmp/manifests-backup/*.yaml /etc/kubernetes/manifests/

# 5. verify
kubectl get nodes && kubectl get pods -A
```

## Automate it (CronJob sketch)
```
   schedule etcdctl snapshot save every N hours
        -> push the .db to S3/GCS (encrypted, versioned, lifecycle-expired)
        -> alert if a backup is missing or 'snapshot status' fails
        -> quarterly: actually RESTORE into a scratch cluster and verify
```

## Common pitfalls
```
   - wrong/old cert paths        -> "context deadline exceeded" — read the manifest
   - forgot ETCDCTL_API=3        -> v2 syntax errors
   - restored over the live dir  -> always restore to a NEW --data-dir
   - HA etcd restore             -> restore one member, then re-add peers cleanly
   - backup never tested         -> the #1 real-world failure; rehearse restores
```

## Key takeaways
- **etcd holds all cluster state** — back it up or risk total loss.
- `etcdctl snapshot save` (with the etcd certs) creates the backup; verify with `snapshot status`.
- Restore writes to a **new --data-dir**; then repoint the etcd static pod.
- Store snapshots **off-node**, encrypted, on a schedule.
- An **untested** backup doesn't count — rehearse the restore.

## Checklist
- [ ] Read etcd endpoints + cert paths from `/etc/kubernetes/manifests/etcd.yaml`
- [ ] Took a snapshot with `etcdctl snapshot save` and checked its status
- [ ] Copied the snapshot off the node (encrypted)
- [ ] Restored into a new data dir and repointed the etcd static pod
- [ ] Verified the cluster came back (`kubectl get nodes`, objects intact)
