# Day 28 — Docker Storage Fundamentals

> Video: Day 28/40 — Docker Volume, Bind Mount, Persistent Storage
> https://www.youtube.com/watch?v=ZAPX21TMkkQ
> Duration: ~15 min

## The problem: containers are ephemeral
When a container is removed, everything written inside it is **gone**. To keep
data (databases, uploads, logs) we must store it **outside** the container's
writable layer.

## Docker's layered architecture
An image is **read-only layers** stacked up; the running container adds one thin
**writable layer** on top (copy-on-write).

```
   +-------------------------------+  <- container WRITABLE layer (ephemeral)
   |  R/W layer (your changes)     |
   +-------------------------------+
   |  image layer: app             |  \
   |  image layer: deps            |   |  READ-ONLY, shared between
   |  image layer: base OS         |  /   containers from same image
   +-------------------------------+
```

- **Copy-on-write:** editing a file from a lower layer copies it up into the R/W
  layer first. Delete the container -> the R/W layer (and your data) disappears.
- Many containers share the same read-only layers (efficient on disk).

## Two ways to persist data
```
   VOLUME (managed by Docker)        BIND MOUNT (a host path you choose)
   /var/lib/docker/volumes/...       /home/me/data  ->  /app/data
   - Docker owns the location        - you control the exact host path
   - portable, easy to back up       - great for local dev (live code)
   - preferred for production data    - tightly coupled to the host layout
```

```
   +-----------+        +---------------------------+
   | container | -----> | volume / host directory    |  survives container
   |  /app/data|        | (outside the writable layer)|  removal
   +-----------+        +---------------------------+
```

## Named volumes
```bash
docker volume create appdata
docker volume ls
docker volume inspect appdata

# mount it into a container
docker run -d --name db -v appdata:/var/lib/mysql mysql:8

# data persists across container re-creation
docker rm -f db
docker run -d --name db -v appdata:/var/lib/mysql mysql:8   # same data
```

## Bind mounts
```bash
# host path : container path  (live editing during development)
docker run -d --name web \
  -v /home/me/site:/usr/share/nginx/html:ro \
  nginx
```
`:ro` = read-only inside the container.

## tmpfs (in-memory, not persistent)
```bash
docker run --tmpfs /cache busybox     # fast scratch space, lost on stop
```

## Volume vs bind mount — when to use which
```
   Volume     -> production data you want Docker to manage & back up
   Bind mount -> local dev, sharing source code / config from the host
   tmpfs      -> sensitive or temporary data that must not hit disk
```

## Key takeaways
- Container writable layer is **ephemeral**; use storage to persist data.
- Images are **read-only layers**, containers add a **copy-on-write** layer.
- **Volumes** (Docker-managed) are preferred for real data; **bind mounts** map a
  host path (ideal for dev); **tmpfs** is in-memory only.
- This sets up Kubernetes volumes / PV / PVC (Day 29).

## Checklist
- [ ] Explained why container data is lost on removal
- [ ] Created a named volume and proved data survives `docker rm`
- [ ] Used a bind mount with `:ro`
- [ ] Can choose volume vs bind mount vs tmpfs for a scenario
