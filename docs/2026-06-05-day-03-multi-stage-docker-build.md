# Day 3 — Multi-Stage Docker Build

> Video: Day 3/40 — Multi Stage Docker Build
> https://www.youtube.com/watch?v=ajetvJmBvFo
> Duration: ~19 min

## Problem: fat images
A single-stage build ships **build tools + source + dependencies** in the final
image. Result: huge, slower, larger attack surface.

## Solution: multi-stage builds
Use multiple `FROM` stages. Build in one stage, copy only the **final
artifact** into a tiny runtime stage.

## Single-stage vs Multi-stage (ASCII)

```
   SINGLE STAGE                         MULTI STAGE
   ============                         ===========
  +---------------------+        STAGE 1 (builder)      STAGE 2 (runtime)
  | base image          |        +-----------------+    +----------------+
  | + compiler/SDK      |        | node:18 (big)   |    | nginx:alpine   |
  | + source code       |        | npm ci          |    | (tiny)         |
  | + node_modules      |  --->  | npm run build   | -> | COPY --from=0  |
  | + build artifacts   |        | => /app/dist    |    |    /app/dist   |
  +---------------------+        +-----------------+    +----------------+
        ~1 GB                       discarded            ~25 MB final
```

## Example: build a React/Vite app, serve with nginx
```dockerfile
# ---- Stage 1: build ----
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build          # outputs to /app/dist

# ---- Stage 2: runtime ----
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Example: Go binary (even smaller)
```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /app/server

FROM scratch                 # empty base = minimal
COPY --from=build /app/server /server
ENTRYPOINT ["/server"]
```

## Key flag: `COPY --from=<stage>`
```
  COPY --from=builder  /app/dist   /usr/share/nginx/html
              ^source stage  ^path in that stage   ^dest in final image
```

## Build & verify size
```bash
docker build -t myapp:multi .
docker images myapp           # compare sizes vs single-stage
```

## Benefits
```
  + Smaller images        -> faster pulls / deploys
  + No build tools shipped -> smaller attack surface
  + One Dockerfile         -> build + package in one place
```

## Key takeaways
- Name stages with `AS <name>`, pull artifacts with `COPY --from=<name>`.
- Final stage should be a **minimal runtime** (alpine / scratch / distroless).
- Build-time deps never reach production.

## Checklist
- [ ] Converted a single-stage Dockerfile to multi-stage
- [ ] Confirmed final image is dramatically smaller
- [ ] Understand `COPY --from=` and named stages
