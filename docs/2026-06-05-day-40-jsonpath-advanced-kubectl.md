# Day 40 — JSONPath & Advanced kubectl

> Video: Day 40/40 — JSONPath, advance kubectl commands
> 40 Days of Kubernetes playlist:
> https://www.youtube.com/playlist?list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC

## Problem & solution
`kubectl get` prints a fixed table, but you often need one specific field across
many objects — an image, a node IP, a Secret value — for scripts or the exam's
"output X to a file" tasks. **JSONPath**, custom columns, and sort/filter flags
turn kubectl into a precise query tool, fast.

**Solution:** Query the API precisely with JSONPath, custom-columns, and sort/label/field selectors, and scaffold manifests fast with --dry-run=client -o yaml.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +---------------------------------- CLUSTER -----------------------------------+
   | +----------------------------- CONTROL PLANE ------------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+           | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr |           | |
   | | +------------+   +------+   +-----------+   +----------------+           | |
   | | api-server  <== kubectl queries the API; JSONPath filters the JSON reply | |
   | +--------------------------------------------------------------------------+ |
   | + WORKER NODE   (kubelet | kube-proxy | runtime) +                           |
   | | + namespace: default +                         |                           |
   | | | +----- POD -----+  |                         |                           |
   | | | | + CONTAINER + |  |                         |                           |
   | | | | | app       | |  |                         |                           |
   | | | | +-----------+ |  |                         |                           |
   | | | +---------------+  |                         |                           |
   | | +--------------------+                         |                           |
   | +------------------------------------------------+                           |
   +------------------------------------------------------------------------------+
```

## JSON vs YAML (same data, two skins)
```
   YAML                         JSON
   metadata:                    { "metadata": {
     name: nginx                    "name": "nginx",
     labels:                        "labels": { "app": "web" } } }
       app: web
```
kubectl talks JSON to the api-server; YAML is just a friendlier surface. Get the
raw shape with `kubectl get pod nginx -o json` to know what to query.

## JSONPath basics
```
   $            the root           .items[*]    every element of a list
   .a.b         nested field       [0]          first element
   ['a-b']      keys with dashes   ?(@.x=="y")  filter by a condition
   {range}{end} loop with custom separators / newlines
```

```bash
# one field
kubectl get pod nginx -o jsonpath='{.status.podIP}'

# a field across ALL pods, one per line
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.podIP}{"\n"}{end}'

# all container images in the cluster
kubectl get pods -A -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u

# a node's InternalIP (filter on a list by type)
kubectl get node <node> -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}'

# decode a Secret value
kubectl get secret db -o jsonpath='{.data.password}' | base64 -d
```

## Custom columns (table output, your fields)
```bash
kubectl get pods -o custom-columns=\
'NAME:.metadata.name,NODE:.spec.nodeName,IMAGE:.spec.containers[0].image,PHASE:.status.phase'
```

## Sorting & field selectors
```bash
kubectl get pods --sort-by=.metadata.creationTimestamp        # oldest -> newest
kubectl get pods --sort-by='.status.containerStatuses[0].restartCount'
kubectl get pods --field-selector status.phase=Running
kubectl get events --field-selector type=Warning --sort-by=.lastTimestamp
```

## Labels, selectors & quick edits
```bash
kubectl get pods -l app=web,tier!=cache       # label selector (AND, negation)
kubectl get pods -L app                        # show the 'app' label as a column
kubectl label pod nginx env=prod               # add/replace a label
kubectl annotate pod nginx owner=team-a        # add an annotation
```

## Speed flags worth knowing
```bash
kubectl explain deployment.spec.strategy        # field docs without leaving the shell
kubectl get pods -o wide                          # node + IP columns
kubectl get pods -o yaml | kubectl neat 2>/dev/null  # strip noise (if installed)
kubectl get all -A                                # quick inventory
kubectl api-resources                             # names, shortnames, scope of every kind
alias k=kubectl; export do='--dry-run=client -o yaml'   # exam-speed manifest scaffolding
kubectl create deploy web --image=nginx $do > web.yaml
```

## Common pitfalls
```
   - JSONPath quoting in bash        -> wrap the whole expression in single quotes
   - keys with dashes                -> use ['my-key'], not .my-key
   - filtering a list                -> ?(@.type=="InternalIP"), mind the == and quotes
   - Secret value still base64       -> pipe through `base64 -d`
   - --sort-by needs a single path   -> point at one field, not a wildcard list
```

## Key takeaways
- kubectl speaks **JSON**; inspect with `-o json`, then query with **JSONPath**.
- `{range .items[*]}...{end}` iterates lists; `?(@.k=="v")` filters them.
- **custom-columns** make your own tables; **--sort-by** orders them.
- **Label selectors** (`-l`) and **field selectors** filter what you fetch.
- `--dry-run=client -o yaml` scaffolds manifests fast (exam gold).

## Checklist
- [ ] Extracted a single field with `-o jsonpath`
- [ ] Looped over `.items[*]` to print a field per object
- [ ] Filtered a list with `?(@.type=="InternalIP")`
- [ ] Built a custom-columns view and a `--sort-by` query
- [ ] Decoded a Secret and scaffolded a manifest with `--dry-run=client -o yaml`
