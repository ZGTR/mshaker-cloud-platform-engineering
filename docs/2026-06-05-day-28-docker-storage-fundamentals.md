# Day 28 — Docker Storage Fundamentals

> Video: Day 28/40 — Docker Volume, Bind Mount, Persistent Storage
> https://www.youtube.com/watch?v=ZAPX21TMkkQ
> Duration: ~15 min

## Problem & solution
Containers are ephemeral, so anything written inside is lost when the container
is removed. Databases, uploads, and logs must persist outside the container's
writable layer to survive restarts and recreation.

**Solution:** Use Docker volumes (or bind mounts) to persist data outside the container's writable layer so it survives container removal.

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
Docker keeps data alive with **volumes** (Docker manages the location) or
**bind mounts** (you point at an exact host path).

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
A **named volume** is created and tracked by Docker, and its data survives
container removal and re-creation.

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
A **bind mount** maps a chosen host directory into the container, ideal for live
editing source or config during development.

```bash
# host path : container path  (live editing during development)
docker run -d --name web \
  -v /home/me/site:/usr/share/nginx/html:ro \
  nginx
```
`:ro` = read-only inside the container.

## tmpfs (in-memory, not persistent)
A **tmpfs** mount lives in RAM only — fast scratch space that never hits disk and
is lost when the container stops.

```bash
docker run --tmpfs /cache busybox     # fast scratch space, lost on stop
```

## Volume vs bind mount — when to use which
Pick the storage type by intent: managed data, host-coupled dev files, or
throwaway in-memory scratch.

```
   Volume     -> production data you want Docker to manage & back up
   Bind mount -> local dev, sharing source code / config from the host
   tmpfs      -> sensitive or temporary data that must not hit disk
```

## An example of each

### Volume — production data Docker manages & backs up
A Postgres database whose data must survive container re-creation and be easy to
back up. Docker owns the location; you snapshot it without touching the host.

```bash
# 1. named volume holds the DB files
docker volume create pgdata
docker run -d --name pg -e POSTGRES_PASSWORD=secret \
  -v pgdata:/var/lib/postgresql/data postgres:16

# 2. write data, then destroy + recreate the container — data persists
docker exec -it pg psql -U postgres -c "create table t(x int); insert into t values (1);"
docker rm -f pg
docker run -d --name pg -e POSTGRES_PASSWORD=secret \
  -v pgdata:/var/lib/postgresql/data postgres:16
docker exec -it pg psql -U postgres -c "select * from t;"   # row still there

# 3. back the volume up to a tarball (portable, off-host)
docker run --rm -v pgdata:/data -v "$PWD":/backup busybox \
  tar czf /backup/pgdata-$(date +%F).tgz -C /data .
```

### Bind mount — local dev, live source from the host
A Node app you edit on your laptop and want reloaded instantly inside the
container, no rebuild. The container reads your real working directory.

```bash
# host source : container path  -> edits on the host appear immediately
docker run -d --name web -p 3000:3000 \
  -v "$PWD/src":/app/src \
  -v /app/node_modules \          # keep the image's node_modules, not the host's
  node:20 npm run dev

# edit ./src/index.js on the host -> the dev server hot-reloads in the container
```

### tmpfs — sensitive / temporary data that must not hit disk
A short-lived secret or scratch buffer that should live only in RAM and vanish
when the container stops (never written to the host disk).

```bash
docker run -d --name worker \
  --tmpfs /run/secrets:rw,size=16m,mode=0700 \
  myapp:latest
# /run/secrets is RAM-only: fast, wiped on stop, never persisted to disk
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
