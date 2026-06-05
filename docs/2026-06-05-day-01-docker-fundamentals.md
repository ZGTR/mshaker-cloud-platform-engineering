# Day 1 — Docker Fundamentals

> Video: Day 1/40 — Docker Tutorial For Beginners — Docker Fundamentals
> https://www.youtube.com/watch?v=ul96dslvVwY
> Duration: ~25 min

## Why containers?
"It works on my machine" problem. A container packages **app + dependencies +
runtime** into one portable unit that runs the same everywhere.

## VM vs Container (ASCII)

```
        VIRTUAL MACHINES                     CONTAINERS
  +-------------------------+        +-------------------------+
  | App A | App B | App C   |        | App A | App B | App C   |
  +-------+-------+---------+        +-------+-------+---------+
  | Bins  | Bins  | Bins    |        | Bins  | Bins  | Bins    |
  +-------+-------+---------+        +-------------------------+
  | Guest | Guest | Guest   |        |   Docker Engine         |
  |  OS   |  OS   |  OS     |        +-------------------------+
  +-------+-------+---------+        |     Host OS             |
  |      Hypervisor         |        +-------------------------+
  +-------------------------+        |     Hardware            |
  |       Host OS           |        +-------------------------+
  +-------------------------+
  |       Hardware          |        Lightweight: share host
  +-------------------------+        kernel, no guest OS.
   Heavy: full OS per VM
```

## Core concepts

```
   Dockerfile  --build-->  Image  --run-->  Container
   (recipe)                (template)       (running instance)

   Registry (Docker Hub) <--push/pull--> your local images
```

- **Image**: read-only template (layers).
- **Container**: a running, writable instance of an image.
- **Registry**: stores/serves images (Docker Hub, ECR, GHCR...).

## Docker architecture

```
   docker CLI  ---REST API--->  Docker Daemon (dockerd)
                                   |       |       |
                                Images  Containers Networks/Volumes
                                   ^
                                   | pull/push
                                Registry (Docker Hub)
```

## Essential commands
```bash
docker pull nginx                 # download image
docker images                     # list local images
docker run -d --name web -p 8080:80 nginx   # run detached, map ports
docker ps                         # running containers
docker ps -a                      # all (incl. stopped)
docker exec -it web bash          # shell into container
docker logs web                   # view logs
docker stop web && docker rm web  # stop + remove
docker rmi nginx                  # remove image
```

## Port mapping (ASCII)
```
   Host :8080  ->  Container :80
   curl localhost:8080  ====>  nginx inside container
```

## Image layers
Each Dockerfile instruction = a cached layer. Reused across builds = fast.
```
  +-----------------------------+  <- CMD ["nginx"]
  +-----------------------------+  <- COPY app
  +-----------------------------+  <- RUN apt-get install
  +-----------------------------+  <- FROM ubuntu (base)
        layers stack up
```

## Key takeaways
- Containers share the host kernel -> lightweight, fast to start.
- Image = build-time artifact; Container = run-time instance.
- `-d` detached, `-p host:container` ports, `-it` interactive shell.

## Checklist
- [ ] Ran an nginx container and hit it on localhost
- [ ] Used `exec`, `logs`, `ps`, `stop`, `rm`
- [ ] Understand image vs container vs registry
