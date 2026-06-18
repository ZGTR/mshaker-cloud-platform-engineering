# Day 1 — Docker Fundamentals

> Video: Day 1/40 — Docker Tutorial For Beginners — Docker Fundamentals
> https://www.youtube.com/watch?v=ul96dslvVwY
> Duration: ~25 min

## Key terms
| Term | Meaning |
| --- | --- |
| Image | Read-only template (app + dependencies) used to start containers |
| Container | A running, isolated instance of an image |
| Dockerfile | The recipe that builds an image |
| Registry | A store for images (e.g. Docker Hub) |
| Layer | A cached filesystem diff that makes up an image |
| Daemon | The `dockerd` background service that builds and runs containers |
| Host kernel | The OS kernel shared by all containers on a host |

## Problem & solution
Software that runs on one machine often breaks on another because of differing
OS versions, libraries, and runtimes (the "works on my machine" problem). We
need a way to package an app with everything it depends on so it runs
identically everywhere.

**Solution:** Package an app with its dependencies into a portable image and run it as an isolated container, so it behaves the same on every machine.

## Why containers?
"It works on my machine" problem. A container packages **app + dependencies +
runtime** into one portable unit that runs the same everywhere.

## VM vs Container (ASCII)
**VMs** virtualize the hardware and run a full guest OS each; **containers**
virtualize the OS and share the host kernel, so they are far lighter.

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
The Docker workflow is a pipeline: a **Dockerfile** builds an image, and an
image runs as a container.

```
   Dockerfile  --build-->  Image  --run-->  Container
   (recipe)                (template)       (running instance)

   Registry (Docker Hub) <--push/pull--> your local images
```

- **Image**: read-only template (layers).
- **Container**: a running, writable instance of an image.
- **Registry**: stores/serves images (Docker Hub, ECR, GHCR...).

## Docker architecture
Docker is **client-server**: the `docker` CLI sends commands over a REST API to
the daemon, which does the real work.

```
   docker CLI  ---REST API--->  Docker Daemon (dockerd)
                                   |       |       |
                                Images  Containers Networks/Volumes
                                   ^
                                   | pull/push
                                Registry (Docker Hub)
```

## Essential commands
These are the everyday commands for pulling, running, inspecting, and cleaning
up containers.

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
**Port mapping** publishes a container's internal port to a port on the host so
you can reach the app from outside.

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
