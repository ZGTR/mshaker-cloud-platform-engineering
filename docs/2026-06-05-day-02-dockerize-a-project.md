# Day 2 — How To Dockerize a Project

> Video: Day 2/40 — How To Dockerize a Project
> https://www.youtube.com/watch?v=nfRsPiRGx74
> Duration: ~35 min

## Problem & solution
Knowing what a container is doesn't help until you can package your *own* app
into one. Without a repeatable build-and-ship process, turning source code into
a portable image and getting it into a registry is ad hoc and error-prone.

**Solution:** Write a Dockerfile (base image, copy code, install deps, set the start command), then build, tag, and push it to a registry.

## Goal
Take a real app (e.g. a Node.js project), write a **Dockerfile**, build an
image, run it, and push it to Docker Hub.

## The Dockerize flow (ASCII)
Dockerizing an app is a four-step pipeline: write a **Dockerfile**, build an
image, run a container, then push to a registry.

```
  Source code
      |
      v
  +-----------+      docker build -t app:1 .     +-----------+
  | Dockerfile| ------------------------------->  |   Image   |
  +-----------+                                   +-----------+
                                                       |
                                          docker run -p 3000:3000 app:1
                                                       v
                                                 +-----------+
                                                 | Container |
                                                 +-----------+
                                                       |
                                       docker push user/app:1
                                                       v
                                                 +-----------+
                                                 |  Registry |
                                                 +-----------+
```

## Common Dockerfile instructions
These are the **core instructions** you combine to describe how an image is
built and run.

```
  FROM        base image to start from
  WORKDIR     set working directory inside the image
  COPY/ADD    copy files from host into image
  RUN         execute a command at BUILD time (creates a layer)
  ENV         set environment variables
  EXPOSE      document the port the app listens on
  CMD         default command at RUN time (can be overridden)
  ENTRYPOINT  fixed command at RUN time (args appended)
```

## Example Dockerfile (Node.js)
A typical **Node.js Dockerfile** installs dependencies first, then copies the
source, to make the most of layer caching.

```dockerfile
FROM node:18-alpine
WORKDIR /app

# copy manifests first to leverage layer caching
COPY package*.json ./
RUN npm install

# then copy the rest of the source
COPY . .

EXPOSE 3000
CMD ["node", "index.js"]
```

## Why copy package.json first? (layer caching)
Copying manifests before the source means **dependency installs are cached** and
only rerun when dependencies actually change.

```
  Change source code only:
  +-------------------+  <- COPY . .          (rebuilt)
  +-------------------+  <- RUN npm install   (CACHED - deps unchanged)
  +-------------------+  <- COPY package.json (CACHED)
  +-------------------+  <- FROM node         (CACHED)

  => npm install is skipped on rebuild = much faster.
```

## Build, run, push
Once the Dockerfile exists, you **build** the image, **run** it locally to test,
then **tag and push** it to Docker Hub.

```bash
docker build -t myapp:1.0 .
docker run -d -p 3000:3000 --name myapp myapp:1.0
curl localhost:3000

# tag + push to Docker Hub
docker login
docker tag myapp:1.0 <dockerhub-user>/myapp:1.0
docker push <dockerhub-user>/myapp:1.0
```

## .dockerignore (don't ship junk)
A **.dockerignore** file excludes files from the build context, just like
`.gitignore` does for git.

```
node_modules
.git
Dockerfile
*.log
.env
```
Keeps the build context small and avoids leaking secrets.

## CMD vs ENTRYPOINT (ASCII)
**CMD** sets a default that arguments fully replace, while **ENTRYPOINT** sets a
fixed command that arguments are appended to.

```
  CMD ["node","index.js"]          docker run img otherarg
       \__ fully replaced by "otherarg"

  ENTRYPOINT ["node"]              docker run img index.js
       \__ "index.js" appended -> node index.js
```

## Key takeaways
- Order Dockerfile steps from **least- to most-frequently changed** for caching.
- Use `.dockerignore` to shrink context & protect secrets.
- `EXPOSE` is documentation; `-p` actually publishes the port.

## Checklist
- [ ] Wrote a Dockerfile for a real app
- [ ] Built, ran, and curled it locally
- [ ] Pushed image to Docker Hub
- [ ] Added a `.dockerignore`
