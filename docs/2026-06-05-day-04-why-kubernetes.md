# Day 4 — Why Kubernetes Is Used

> Video: Day 4/40 — Why Kubernetes Is Used — Simply Explained
> https://www.youtube.com/watch?v=lXs1VCWqIH4
> Duration: ~8 min

## The problem with plain Docker at scale
Docker runs containers on **one host**. In production you need many containers
across many machines, with self-healing, scaling, and zero-downtime updates.
Doing this by hand does not scale.

## What breaks without an orchestrator (ASCII)

```
   Plain Docker, single host:
   +------------------ Host ------------------+
   |  [c1] [c2] [c3]                           |
   |   x  <- container crashes... who restarts?|
   |   Host dies -> ALL containers gone        |
   |   Traffic spike -> manual scaling         |
   +-------------------------------------------+
```

## What Kubernetes gives you

```
                +--------------------------------------+
                |            KUBERNETES                 |
                |  desired state == actual state loop   |
                +--------------------------------------+
                  |        |         |          |
          Self-heal   Auto-scale   Rolling    Load
          (restart    (HPA up/     updates    balance
           crashed     down)       & rollback  traffic
           pods)
```

- **Self-healing**: restarts/replaces failed containers & nodes.
- **Horizontal scaling**: add/remove replicas on demand.
- **Service discovery + load balancing**: stable names, spread traffic.
- **Automated rollouts/rollbacks**: ship safely, revert fast.
- **Config & secret management**: decouple config from images.
- **Storage orchestration**: attach volumes automatically.

## Desired vs actual state (the core idea)

```
   You declare:   "I want 3 replicas of myapp"
                          |
                          v
   +--------------------------------------------+
   |  K8s control loop: observe -> compare -> act|
   +--------------------------------------------+
       actual = 2 ?  -> create 1 more
       actual = 4 ?  -> delete 1
       pod crashed?  -> recreate
```

You describe the **end state**; Kubernetes continuously works to make reality
match it. This is "declarative" management.

## When do you NOT need Kubernetes?
- A single small app / hobby project -> Docker or a PaaS is simpler.
- K8s adds real operational complexity; use it when scale/resilience demands it.

## Key takeaways
- Kubernetes = **container orchestrator** for many hosts.
- It enforces a **desired state** via continuous control loops.
- Core wins: self-healing, scaling, rollouts, service discovery.

## Checklist
- [ ] Can explain self-healing and desired-state in one sentence each
- [ ] Understand why single-host Docker is not enough at scale
