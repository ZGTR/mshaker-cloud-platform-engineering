"""Standard ASCII diagram toolkit for the Kubernetes study docs.

Single source of truth for the cluster entities drawn across all day docs so
the same boxes (api-server, etcd, scheduler, controller-mgr, node, namespace,
pod, container) look identical everywhere.

Two families:
  * cluster_map(notes)            -> nested-box "where this fits" topology
  * sequence(actors, steps, tail) -> lifeline flow / attack diagrams

Run gen.py to print the standardized blocks used in the docs.
"""

# ---------------------------------------------------------------- box tree ---
# node kinds: ("text", s) | ("raw", [lines]) | ("row", [nodes]) | ("box", title, [items])

def txt(s):            return ("text", s)
def raw(lines):        return ("raw", list(lines))
def row(*nodes):       return ("row", list(nodes))
def box(title, *items):return ("box", title, list(items))

def tok(name):
    """A small standalone bordered token, e.g. a control-plane component."""
    w = len(name) + 2
    return raw(["+" + "-" * w + "+",
                "| " + name + " |",
                "+" + "-" * w + "+"])

def render(node):
    kind = node[0]
    if kind == "text":
        return [node[1]]
    if kind == "raw":
        return list(node[1])
    if kind == "row":
        blocks = [render(n) for n in node[1]]
        h = max(len(b) for b in blocks)
        padded = []
        for b in blocks:
            w = max((len(x) for x in b), default=0)
            b = [x.ljust(w) for x in b] + [" " * w] * (h - len(b))
            padded.append(b)
        return ["   ".join(parts).rstrip() for parts in zip(*padded)]
    _, title, items = node
    flat, inner = [], 0
    for it in items:
        for ln in render(it):
            inner = max(inner, len(ln))
            flat.append(ln)
    width = max(inner + 2, len(title) + 2)
    t = " " + title + " "
    dash = width - len(t)
    left = dash // 2
    out = ["+" + "-" * left + t + "-" * (dash - left) + "+"]
    for ln in flat:
        out.append("| " + ln.ljust(width - 2) + " |")
    out.append("+" + "-" * width + "+")
    return out

# ---------------------------------------------------- canonical cluster map ---

def cluster_map(notes=None, ns="default", workload="POD"):
    """Return the canonical cluster topology as rendered lines.

    notes: dict mapping an entity key to a list of "<== ..." annotation lines.
    keys: api-server | etcd | scheduler | controller-mgr | node | namespace
          | pod | container
    """
    notes = notes or {}

    def ann(key):
        return [txt("   <== " + n) for n in notes.get(key, [])]

    container = box("CONTAINER", txt("app"), *ann("container"))
    pod = box(workload, container, *ann("pod"))
    namespace = box("namespace: " + ns, pod, *ann("namespace"))
    node = box("WORKER NODE   (kubelet | kube-proxy | runtime)",
               *(ann("node") + [namespace]))

    cp_items = [row(tok("api-server"), tok("etcd"),
                    tok("scheduler"), tok("controller-mgr"))]
    for key in ("api-server", "etcd", "scheduler", "controller-mgr"):
        for n in notes.get(key, []):
            cp_items.append(txt(key + "  <== " + n))
    control_plane = box("CONTROL PLANE", *cp_items)

    cluster = box("CLUSTER", control_plane, node)
    return render(cluster)

# ----------------------------------------------------- sequence / lifelines ---

def sequence(actors, steps, tail=None):
    """Lifeline flow diagram.

    actors: list of names (left->right)
    steps:  list of ops:
            ("msg", src, dst, [label lines])
            ("note", [lines])
            ("gap",)
    tail:   plain lines printed under the diagram (e.g. "STOPPED BY: ...")
    """
    tail = tail or []
    start, center = {}, {}
    pos, GAP = 0, 8
    for a in actors:
        w = len(a) + 4
        start[a] = pos
        center[a] = pos + w // 2
        pos += w + GAP
    total = pos
    need = total
    for op in steps:
        if op[0] == "msg":
            lo = min(center[op[1]], center[op[2]])
            for lab in op[3]:
                need = max(need, lo + 2 + len(lab) + 2)
        elif op[0] == "note":
            for lab in op[1]:
                need = max(need, 2 + len(lab) + 2)
    canvas = need

    def blank():
        return [" "] * canvas

    def lifelines(r):
        for a in actors:
            r[center[a]] = "|"

    def put(r, col, s):
        for i, ch in enumerate(s):
            if 0 <= col + i < len(r):
                r[col + i] = ch

    out = []
    top, mid, bot = blank(), blank(), blank()
    for a in actors:
        s, w = start[a], len(a) + 4
        put(top, s, "+" + "-" * (w - 2) + "+")
        put(mid, s, "| " + a + " |")
        put(bot, s, "+" + "-" * (w - 2) + "+")
    out += ["".join(r).rstrip() for r in (top, mid, bot)]

    def life():
        r = blank(); lifelines(r); return r

    out.append("".join(life()).rstrip())
    for op in steps:
        if op[0] == "msg":
            _, srcn, dstn, labels = op
            cs, cd = center[srcn], center[dstn]
            lo, hi = sorted([cs, cd])
            for lab in labels:
                r = life(); put(r, lo + 2, lab); out.append("".join(r).rstrip())
            r = life()
            for x in range(lo + 1, hi):
                r[x] = "-"
            if cs < cd:
                r[hi - 1] = ">"
            else:
                r[lo + 1] = "<"
            out.append("".join(r).rstrip())
            out.append("".join(life()).rstrip())
        elif op[0] == "note":
            for lab in op[1]:
                r = life(); put(r, 2, lab); out.append("".join(r).rstrip())
            out.append("".join(life()).rstrip())
        elif op[0] == "gap":
            out.append("".join(life()).rstrip())
    out += list(tail)
    return out
