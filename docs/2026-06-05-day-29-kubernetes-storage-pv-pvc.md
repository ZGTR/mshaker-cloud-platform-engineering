# Day 29 — Storage in Kubernetes (Volumes, PV, PVC, StorageClass)

> Video: Day 29/40 — Kubernetes Volume Simplified | PV, PVC & Storage Class
> https://www.youtube.com/watch?v=2NzYX8_lX_0
> Duration: ~28 min

## Why pods need volumes
A container's filesystem dies with it, and a pod can be rescheduled anytime.
**Volumes** decouple data from the container lifecycle.

```
   emptyDir  -> scratch space, lives with the POD (gone when pod dies)
   hostPath  -> a directory on the NODE (tied to that one node)
   PV / PVC  -> real, durable storage that outlives pods (and nodes)
```

## Non-persistent: emptyDir
Good for cache / scratch / sharing files between containers in the same pod.
```yaml
spec:
  containers:
    - name: redis
      image: redis
      volumeMounts:
        - name: redis-storage
          mountPath: /data/redis
  volumes:
    - name: redis-storage
      emptyDir: {}            # deleted when the pod is removed
```

## The PV / PVC model
Separation of concerns:
```
   PersistentVolume (PV)        = the actual storage (admin/cluster supplies it)
   PersistentVolumeClaim (PVC)  = a request for storage (the app/dev asks)
   Pod                          = mounts the PVC

   Pod  --uses-->  PVC  --binds-->  PV  --backed by-->  disk / NFS / cloud
```

> The PVC is matched to a PV with enough **capacity** and compatible
> **accessModes** + **storageClassName**, then they **bind** 1:1.

## Access modes
A volume's **access mode** declares how many nodes can mount it and whether they
get read-write or read-only access.

```
   RWO  ReadWriteOnce      -> mounted read-write by ONE node
   ROX  ReadOnlyMany       -> read-only by MANY nodes
   RWX  ReadWriteMany      -> read-write by MANY nodes (needs NFS-like backend)
```

## Reclaim policy (what happens when the PVC is deleted)
The **reclaim policy** decides the fate of the PV and its data once the claim is
removed.

```
   Retain  -> keep the PV + data (manual cleanup) — safest
   Delete  -> delete the PV and the underlying storage
   Recycle -> deprecated
```

## Sample PV (hostPath, for a demo)
The **PV** is the supply side: it declares capacity, access mode, and the
backing storage (here a node `hostPath` for simplicity).

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: task-pv-volume
  labels:
    type: local
spec:
  storageClassName: standard
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/home/ubuntu/day29-storage-k8s"
```

## Sample PVC (the request)
The **PVC** is the demand side: the app asks for a size, access mode, and class,
and Kubernetes binds it to a matching PV.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: task-pv-claim
spec:
  storageClassName: standard
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi          # binds to a PV with >= this capacity
```

## Pod that mounts the PVC
The pod references the PVC by name in `volumes`, then mounts it into a container
path — it never touches the PV directly.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: task-pv-pod
spec:
  volumes:
    - name: task-pv-storage
      persistentVolumeClaim:
        claimName: task-pv-claim
  containers:
    - name: task-pv-container
      image: nginx
      ports:
        - containerPort: 80
      volumeMounts:
        - mountPath: "/usr/share/nginx/html"
          name: task-pv-storage
```

```bash
kubectl get pv,pvc
# STATUS Bound means the PVC found and claimed a PV
```

## Static vs dynamic provisioning
PVs can be **hand-created** by an admin ahead of time, or **auto-created** on
demand by a StorageClass when a PVC appears.

```
   STATIC  -> admin pre-creates PVs by hand (like the demo above)
   DYNAMIC -> a StorageClass auto-creates a PV when a PVC is made
```

StorageClass = a **template/provisioner** for on-demand volumes:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: kubernetes.io/aws-ebs   # or a CSI driver
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
```
> A PVC that names a StorageClass gets its PV created automatically — no admin
> step. The cluster's **default** StorageClass is used when none is specified.

## Key takeaways
- `emptyDir` = pod-scoped scratch; `hostPath` = one node; **PV/PVC** = durable.
- **PV = supply, PVC = demand**; they bind 1:1 on capacity + accessMode + class.
- **Access modes** RWO/ROX/RWX; **reclaim** Retain/Delete.
- **Static** = hand-made PVs; **dynamic** = StorageClass provisions on demand.

## Checklist
- [ ] Used an `emptyDir` and saw it vanish with the pod
- [ ] Created a PV + PVC and confirmed STATUS `Bound`
- [ ] Mounted the PVC in a pod and wrote/read data
- [ ] Explained static vs dynamic provisioning and StorageClasses
