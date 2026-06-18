"""Generate the standardized ASCII blocks used across the day docs.

Usage:
    python3 gen.py            # print every block, labelled
    python3 gen.py day16      # print one block
"""
import sys
from k8sdiagram import cluster_map, sequence

# ------------------------------------------------ cluster-map focus per day ---
# Each entry is the dict of "<== " annotations layered onto the SAME canonical
# topology, so every doc shows the identical entities.
MAPS = {}
MAPS["day04"] = {"scheduler": ["an orchestrator places work for you"],
                 "controller-mgr": ["self-healing + scaling, not by hand"]}
MAPS["day05"] = {"api-server": ["front door: everything talks here"],
                 "etcd": ["key-value store of ALL cluster state"],
                 "scheduler": ["assigns pods to nodes"],
                 "controller-mgr": ["drives actual state -> desired state"],
                 "node": ["runs the actual workloads"],
                 "pod": ["smallest deployable unit"],
                 "container": ["your app image"]}
MAPS["day06"] = {"node": ["with kind, each NODE runs as a Docker container"]}
MAPS["day07"] = {"pod": ["smallest deployable unit"],
                 "container": ["shares network + storage with pod siblings"]}
MAPS["day08"] = {"controller-mgr": ["Deployment -> ReplicaSet keeps N pods alive"],
                 "pod": ["one of N identical replicas"]}
MAPS["day09"] = {"namespace": ["a Service gives a stable IP/DNS in front of pods"],
                 "pod": ["selected by the Service via labels"]}
MAPS["day10"] = {"namespace": ["logical boundary: dev / staging / prod"]}
MAPS["day11"] = {"container": ["init runs first; sidecar runs alongside the app"]}
MAPS["day12"] = {"controller-mgr": ["DaemonSet / Job / CronJob controllers"],
                 "node": ["DaemonSet = exactly one pod per node"],
                 "pod": ["Job / CronJob pods run to completion"]}
MAPS["day13"] = {"scheduler": ["bypassed by static pods + nodeName"],
                 "node": ["kubelet reads /etc/kubernetes/manifests -> static pod"]}
MAPS["day14"] = {"scheduler": ["checks node taints vs pod tolerations"],
                 "node": ["a taint repels pods unless they tolerate it"]}
MAPS["day15"] = {"scheduler": ["matches pod affinity against node labels"],
                 "node": ["labeled (e.g. disktype=ssd) so pods can target it"]}
MAPS["day16"] = {"scheduler": ["sums pod REQUESTS vs node free capacity"],
                 "container": ["requests = reserved; limits = hard ceiling"]}
MAPS["day17"] = {"controller-mgr": ["HPA / VPA controllers + metrics-server"],
                 "pod": ["HPA changes the NUMBER of pods"],
                 "container": ["VPA changes the SIZE (requests/limits)"]}
MAPS["day18"] = {"node": ["kubelet runs the probes on a schedule"],
                 "container": ["liveness restarts; readiness gates traffic"]}
MAPS["day19"] = {"etcd": ["stores ConfigMap (plain) + Secret (base64)"],
                 "container": ["consumes config as env vars or mounted files"]}
MAPS["day20"] = {"api-server": ["serves HTTPS; verifies client certs"],
                 "etcd": ["TLS to etcd; encrypted at rest"],
                 "node": ["kubelet uses certs to talk to the api-server"],
                 "container": ["app may do its own TLS / mTLS (service mesh)"]}
MAPS["day21"] = {"api-server": ["every component authenticates with a cert"],
                 "etcd": ["TLS + peer certs; holds all Secrets"],
                 "node": ["kubelet has a client cert signed by the cluster CA"]}
MAPS["day22"] = {"api-server": ["every request: authn -> authz -> admission"]}
MAPS["day23"] = {"api-server": ["RBAC authorizes verbs on resources"],
                 "namespace": ["Role + RoleBinding are namespaced"]}
MAPS["day24"] = {"api-server": ["ClusterRole spans ALL namespaces"],
                 "node": ["nodes are cluster-scoped (only a ClusterRole grants them)"]}
MAPS["day25"] = {"api-server": ["validates the ServiceAccount token"],
                 "pod": ["runs as a ServiceAccount identity"]}
MAPS["day26"] = {"namespace": ["NetworkPolicies are namespaced"],
                 "pod": ["a NetworkPolicy is a firewall between pods"]}
MAPS["day27"] = {"api-server": ["kubeadm init bootstraps the control plane"],
                 "node": ["kubeadm join adds worker nodes"]}
MAPS["day29"] = {"pod": ["a PVC binds durable storage that outlives the pod"],
                 "container": ["writes to the mounted volume"]}

MAPS["day30"] = {"namespace": ["CoreDNS (in kube-system) answers DNS for every pod"]}
MAPS["day31"] = {"api-server": ["CoreDNS watches Services + Endpoints here"],
                 "namespace": ["each pod's /etc/resolv.conf points at CoreDNS"]}
MAPS["day32"] = {"node": ["the CNI plugin wires every pod's network namespace"],
                 "container": ["each pod gets its own IP in the pod CIDR"]}
MAPS["day33"] = {"namespace": ["Ingress + controller route external HTTP(S) to Services"],
                 "pod": ["the ingress controller itself runs as pods"]}
MAPS["day34"] = {"api-server": ["kubeadm upgrade: control plane first, one minor at a time"],
                 "node": ["drain -> upgrade kubelet -> uncordon, node by node"]}
MAPS["day35"] = {"etcd": ["etcdctl snapshot save/restore = the cluster backup"]}
MAPS["day36"] = {"controller-mgr": ["metrics-server feeds HPA + 'kubectl top'"],
                 "node": ["kubelet/cAdvisor expose node + pod metrics; logs live here"]}
MAPS["day37"] = {"pod": ["describe / logs / events to diagnose app failures"],
                 "container": ["CrashLoopBackOff, ImagePullBackOff, OOMKilled"]}
MAPS["day38"] = {"api-server": ["control-plane runs as static pods in /etc/kubernetes/manifests"],
                 "node": ["check kubelet + containerd health on each node"]}
MAPS["day39"] = {"node": ["cordon/drain for maintenance; check CNI + kube-proxy"],
                 "namespace": ["Service / DNS / NetworkPolicy are common failure points"]}
MAPS["day40"] = {"api-server": ["kubectl queries the API; JSONPath filters the JSON reply"]}

# ------------------------------------------------------------- sequences -----
SEQS = {}

# Day 20 — generic TLS attack scenarios (CLIENT / ATTACKER / SERVER / CA)
A3 = ["CLIENT", "ATTACKER", "SERVER"]
SEQS["day20-core"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) request"]),
    ("msg", "ATTACKER", "SERVER", ["(2) forwards"]),
    ("msg", "SERVER", "ATTACKER", ["(3) response"]),
    ("msg", "ATTACKER", "CLIENT", ["(4) forwards"]),
    ("note", ["HTTP : attacker READS + REWRITES everything (total compromise)",
              "HTTPS: attacker sees only ciphertext + must impersonate server"])],
    ["STOPPED BY: getting in the middle is easy; TLS makes the position useless."])
SEQS["day20-s1-eavesdrop"] = (A3, [
    ("msg", "CLIENT", "SERVER", ["(1) login: password=hunter2"]),
    ("note", ["(2) ATTACKER copies the bytes off the wire"]),
    ("note", ['PLAIN HTTP -> reads "password=hunter2"',
              'WITH TLS   -> reads "9f#$%enc%$#a1"  (useless)'])],
    ["STOPPED BY: Confidentiality (the symmetric session key)."])
SEQS["day20-s2-impersonation"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) ClientHello"]),
    ("msg", "ATTACKER", "CLIENT", ["(2) cert CN=bank.com, signed by EvilCA"]),
    ("note", ["(3) CLIENT: is EvilCA in my trust store? -> NO",
              "    -> warning / connection ABORTED (real SERVER never reached)"])],
    ["STOPPED BY: Authenticity (cert must chain to a CA you already trust)."])
SEQS["day20-s3-tamper"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) transfer $10"]),
    ("msg", "ATTACKER", "SERVER", ["(2) edited -> transfer $9999"]),
    ("note", ["(3) SERVER checks the TLS record auth tag (AEAD/MAC)",
              "    -> tag mismatch -> record DROPPED"])],
    ["STOPPED BY: Integrity (per-record authentication)."])
SEQS["day20-s4-sslstrip"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) HTTP (no TLS yet)"]),
    ("msg", "ATTACKER", "SERVER", ["(2) HTTPS (real TLS here only)"]),
    ("msg", "SERVER", "ATTACKER", ["(3) HTTPS response"]),
    ("msg", "ATTACKER", "CLIENT", ["(4) HTTP (plaintext)"]),
    ("note", ["CLIENT never upgraded to HTTPS -> steps 1 & 4 are readable"])],
    ["STOPPED BY: HSTS (browser refuses HTTP) + redirects + preload list."])
SEQS["day20-s5-downgrade"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) ClientHello:", "TLS1.3 + strong ciphers"]),
    ("msg", "ATTACKER", "SERVER", ["(2) REWRITES ->", '"only TLS1.0 / export cipher"']),
    ("msg", "SERVER", "CLIENT", ["(3) ServerHello + Finished", "(MAC over whole handshake)"]),
    ("note", ["(4) CLIENT verifies the Finished MAC -> handshake was tampered",
              "    -> ABORT. No weak cipher is ever used."])],
    ["STOPPED BY: downgrade protection (Finished MAC); disable old TLS;",
     "            TLS 1.3 removes weak/export ciphers entirely."])
SEQS["day20-s6-replay"] = (A3, [
    ("msg", "CLIENT", "ATTACKER", ["(1) [encrypted POST /pay]"]),
    ("note", ["(2) ATTACKER records the encrypted bytes"]),
    ("msg", "ATTACKER", "SERVER", ["(3) re-sends them tomorrow"]),
    ("note", ["(4) SERVER: session keys + sequence numbers differ -> REJECT"])],
    ["STOPPED BY: per-session keys + record sequence numbers.",
     "CAVEAT: TLS 1.3 0-RTT early data IS replayable -> never for writes/payments."])
SEQS["day20-s7-stolenkey"] = (["ATTACKER", "SERVER"], [
    ("msg", "ATTACKER", "SERVER", ["(1) steals the server's private .key"]),
    ("note", ["(2) ATTACKER also recorded CLIENT<->SERVER traffic earlier.",
              "    Can it decrypt that PAST traffic now?",
              "    NO forward secrecy : derived from long-term key -> YES (all past)",
              "    WITH FS (ECDHE)    : ephemeral per-session key -> NO"])],
    ["STOPPED/LIMITED BY: ECDHE forward secrecy + key rotation + fast revocation."])
SEQS["day20-s8-rogueca"] = (["ATTACKER", "CA", "CLIENT"], [
    ("msg", "ATTACKER", "CA", ["(1) tricks / hacks the CA"]),
    ("msg", "CA", "ATTACKER", ["(2) mis-issues a cert for bank.com"]),
    ("msg", "ATTACKER", "CLIENT", ['(3) MITM presents that "valid" cert']),
    ("note", ["(4) CLIENT: chain is valid -> ACCEPTS the fake (authenticity bypassed!)"])],
    ["DEFENSES: Certificate Transparency logs + CAA records + public-key pinning."])
SEQS["day20-s9-dvhijack"] = (["ATTACKER", "CA"], [
    ("msg", "ATTACKER", "CA", ["(1) hijacks DNS/BGP for the victim domain"]),
    ("msg", "CA", "ATTACKER", ["(2) ACME http-01/dns-01 challenge"]),
    ("msg", "ATTACKER", "CA", ["(3) passes it (controls the domain right now)"]),
    ("note", ["(4) CA issues a REAL, valid cert for a domain attacker doesn't own"])],
    ["DEFENSES: DNSSEC + CAA records + monitor CT logs for surprise issuance."])

# Day 21 — Kubernetes-actor flows (kubectl / api-server / etcd / kubelet / CA)
SEQS["day21-csr"] = (["kubectl", "api-server", "CA"], [
    ("msg", "kubectl", "api-server", ["(1) submit CertificateSigningRequest (CN=amy/O=devs)"]),
    ("note", ["(2) admin reviews the subject and APPROVES"]),
    ("msg", "api-server", "CA", ["(3) hand approved CSR to the cluster CA"]),
    ("msg", "CA", "api-server", ["(4) CA signs -> certificate"]),
    ("msg", "api-server", "kubectl", ["(5) download signed cert -> kubeconfig"])],
    ["RESULT: amy authenticates as user=amy, group=devs; RBAC decides her powers."])
SEQS["day21-mtls"] = (["kubelet", "api-server", "etcd"], [
    ("msg", "kubelet", "api-server", ["(1) connect + present client cert (system:nodes)"]),
    ("msg", "api-server", "kubelet", ["(2) present server cert; both verify vs cluster CA"]),
    ("msg", "api-server", "etcd", ["(3) api-server is now a CLIENT to etcd (TLS)"]),
    ("note", ["every link is mutual TLS; the cluster CA signs both ends"])],
    ["NOTE: the api-server is a SERVER to kubectl/kubelet and a CLIENT to etcd."])
SEQS["day21-a1-stolen-ca"] = (["ATTACKER", "CA", "api-server"], [
    ("msg", "ATTACKER", "CA", ["(1) reads /etc/kubernetes/pki/ca.key"]),
    ("note", ["(2) signs /CN=evil/O=system:masters  (cluster-admin group)"]),
    ("msg", "ATTACKER", "api-server", ["(3) connects with the forged cert"]),
    ("note", ["(4) cert chains to the cluster CA -> FULL takeover, cannot be revoked"])],
    ["DEFENSE: guard ca.key (root-only / HSM); if leaked, ROTATE the entire CA."])
SEQS["day21-a2-malicious-csr"] = (["ATTACKER", "api-server"], [
    ("msg", "ATTACKER", "api-server", ["(1) submit CSR /CN=mallory/O=system:masters"]),
    ("note", ["(2) admin blindly runs 'kubectl certificate approve'"]),
    ("msg", "api-server", "ATTACKER", ["(3) signed admin cert returned"]),
    ("note", ["(4) mallory is now cluster-admin"])],
    ["DEFENSE: READ every CSR subject; never approve O=system:masters."])
SEQS["day21-a-stolen-kubeconfig"] = (["ATTACKER", "api-server"], [
    ("msg", "ATTACKER", "api-server", ["(1) connects with a stolen kubeconfig / client cert"]),
    ("note", ["(2) is accepted as that user -> can do whatever that user's RBAC allows",
              "    (a leaked cluster-admin kubeconfig == full takeover)"])],
    ["DEFENSE: short-lived certs, least-privilege RBAC, protect kubeconfig,",
     "         rotate/re-issue the CA-signed cert (there is no cert blacklist)."])
SEQS["day21-a3-etcd"] = (["ATTACKER", "etcd"], [
    ("msg", "ATTACKER", "etcd", ["(1) reaches etcd without its client cert"]),
    ("note", ["(2) dumps every Secret in the cluster (base64, not encrypted)"])],
    ["DEFENSE: etcd TLS + firewall to control plane only + encryption-at-rest."])
SEQS["day21-a4-kubelet"] = (["ATTACKER", "kubelet"], [
    ("msg", "ATTACKER", "kubelet", ["(1) hits :10250 with anonymous auth enabled"]),
    ("note", ["(2) exec into pods / read logs / run on the node (no creds)"])],
    ["DEFENSE: --anonymous-auth=false + webhook authz + firewall 10250."])
SEQS["day21-a-anon-apiserver"] = (["ATTACKER", "api-server"], [
    ("msg", "ATTACKER", "api-server", ["(1) calls the API with NO credentials"]),
    ("note", ["(2) lands as user 'system:anonymous' / group 'system:unauthenticated'",
              "    -> dangerous ONLY if a Role/ClusterRole is bound to those names"])],
    ["DEFENSE: --anonymous-auth=false; never bind roles to system:anonymous",
     "         or system:unauthenticated."])


# ---- end-to-end request journeys (user -> server), standardized actors ------
SEQS["day22-e2e"] = (["kubectl", "api-server", "etcd"], [
    ("msg", "kubectl", "api-server", ["(1) kubectl apply -f pod.yaml  (TLS: client cert)"]),
    ("note", ["(2) AUTHN : cert CN=adam, O=devs        -> user 'adam'"]),
    ("note", ["(3) AUTHZ : RBAC -> may adam create pods in 'default'?"]),
    ("note", ["(4) ADMISSION : quotas / policies / defaulting"]),
    ("msg", "api-server", "etcd", ["(5) persist the Pod object"]),
    ("msg", "etcd", "api-server", ["(6) stored (resourceVersion)"]),
    ("msg", "api-server", "kubectl", ["(7) 201 Created"])],
    ["403 Forbidden at step 3 -> NOTHING is written; identity was fine,",
     "the permission was not. AuthN and AuthZ are two separate gates."])
SEQS["day23-e2e"] = (["amy", "api-server"], [
    ("msg", "amy", "api-server", ["(1) kubectl get pods -n dev   (cert O=dev-team)"]),
    ("note", ["(2) AUTHN: user=amy, group=dev-team"]),
    ("note", ["(3) AUTHZ: RoleBinding in 'dev' -> Role 'pod-reader' (get/list pods)"]),
    ("msg", "api-server", "amy", ["(4) 200 OK -> pods in dev listed"]),
    ("msg", "amy", "api-server", ["(5) kubectl get pods -n prod"]),
    ("note", ["(6) no RoleBinding for amy in 'prod'"]),
    ("msg", "api-server", "amy", ["(7) 403 Forbidden"])],
    ["Role + RoleBinding are NAMESPACED: power in 'dev' grants nothing in 'prod'."])
SEQS["day24-e2e"] = (["amy", "api-server"], [
    ("msg", "amy", "api-server", ["(1) kubectl get nodes   (nodes are cluster-scoped)"]),
    ("note", ["(2) AUTHN: user=amy"]),
    ("note", ["(3) AUTHZ: a namespaced Role can NEVER grant 'nodes'"]),
    ("note", ["(4) ClusterRoleBinding -> ClusterRole 'node-reader' (get/list nodes)"]),
    ("msg", "api-server", "amy", ["(5) 200 OK -> all nodes listed (cluster-wide)"])],
    ["Cluster-scoped resources (nodes, PVs, namespaces) need a ClusterRole."])
SEQS["day25-e2e"] = (["pod-app", "api-server"], [
    ("note", ["(0) pod runs as ServiceAccount 'reader' (token auto-mounted)"]),
    ("msg", "pod-app", "api-server", ["(1) GET /api/v1/.../pods  Authorization: Bearer <token>"]),
    ("note", ["(2) AUTHN: token -> system:serviceaccount:default:reader"]),
    ("note", ["(3) AUTHZ: RoleBinding -> Role allows get/list pods"]),
    ("msg", "api-server", "pod-app", ["(4) 200 OK -> pod list"])],
    ["In-cluster apps authenticate as a ServiceAccount, never as a human user."])
SEQS["day26-e2e"] = (["backend", "CNI", "mysql"], [
    ("msg", "backend", "CNI", ["(1) TCP connect to mysql:3306"]),
    ("note", ["(2) CNI evaluates NetworkPolicies selecting mysql"]),
    ("note", ["(3) rule: allow from podSelector app=backend on 3306"]),
    ("msg", "CNI", "mysql", ["(4) backend matches the rule -> ALLOWED"]),
    ("note", ["(5) a 'frontend' pod tries :3306 -> no rule matches"]),
    ("note", ["(6) -> packet DROPPED (frontend connection just times out)"])],
    ["NetworkPolicy = pod-to-pod firewall enforced by the CNI on each node."])
SEQS["day29-e2e"] = (["kubectl", "control-plane", "kubelet"], [
    ("msg", "kubectl", "control-plane", ["(1) apply PVC (request 5Gi)"]),
    ("note", ["(2) provisioner/admin BINDS the PVC -> a PV (dynamic or pre-made)"]),
    ("msg", "kubectl", "control-plane", ["(3) apply Pod that mounts the PVC"]),
    ("msg", "control-plane", "kubelet", ["(4) scheduled; kubelet attaches + mounts the volume"]),
    ("note", ["(5) container writes to /data (lands on the PV)"]),
    ("note", ["(6) pod deleted + recreated -> SAME PV re-mounted, data intact"])],
    ["A PVC binds storage that OUTLIVES the pod; the PV holds the real data."])


SEQS["day30-resolve"] = (["browser", "resolver", "authoritative"], [
    ("msg", "browser", "resolver", ["(1) A? www.example.com"]),
    ("note", ["(2) resolver checks cache; if cold, walks root -> TLD -> authoritative"]),
    ("msg", "resolver", "authoritative", ["(3) who is www.example.com?"]),
    ("msg", "authoritative", "resolver", ["(4) A 93.184.216.34 (TTL 300)"]),
    ("msg", "resolver", "browser", ["(5) 93.184.216.34 (cached for the TTL)"])],
    ["The browser then opens TCP/443 to that IP. /etc/hosts wins before DNS."])
SEQS["day31-dns"] = (["pod", "CoreDNS", "api-server"], [
    ("msg", "pod", "CoreDNS", ["(1) resolve my-svc.dev.svc.cluster.local"]),
    ("note", ["(2) CoreDNS watches Services + Endpoints from the api-server"]),
    ("msg", "CoreDNS", "pod", ["(3) answer: ClusterIP 10.96.12.7"]),
    ("note", ["(4) pod connects to the ClusterIP; kube-proxy load-balances to a real pod"])],
    ["Pods get /etc/resolv.conf pointing at the CoreDNS (kube-dns) ClusterIP."])
SEQS["day33-ingress"] = (["client", "ingress", "service", "pod"], [
    ("msg", "client", "ingress", ["(1) GET https://shop.example.com/cart"]),
    ("note", ["(2) controller matches host + path -> a backend Service; TLS terminates here"]),
    ("msg", "ingress", "service", ["(3) forward to the Service (ClusterIP)"]),
    ("msg", "service", "pod", ["(4) kube-proxy load-balances to a ready pod"]),
    ("msg", "pod", "client", ["(5) 200 OK"])],
    ["One LB + one ingress controller fans out to many Services by host/path."])
SEQS["day34-upgrade"] = (["admin", "control-plane", "worker"], [
    ("msg", "admin", "control-plane", ["(1) apt install kubeadm=1.30; kubeadm upgrade apply v1.30.x"]),
    ("note", ["(2) then upgrade kubelet + kubectl on the control plane, restart kubelet"]),
    ("msg", "admin", "worker", ["(3) kubectl drain <worker> (evict pods safely)"]),
    ("note", ["(4) on the worker: apt install kubelet=1.30; kubeadm upgrade node"]),
    ("msg", "admin", "worker", ["(5) kubectl uncordon <worker> (schedulable again)"])],
    ["One minor at a time; control plane first, then nodes one-by-one."])
SEQS["day35-etcd"] = (["admin", "etcd"], [
    ("msg", "admin", "etcd", ["(1) etcdctl snapshot save backup.db"]),
    ("note", ["(2) copy backup.db OFF the cluster (S3/GCS, encrypted)"]),
    ("note", ["--- disaster: etcd data is lost ---"]),
    ("msg", "admin", "etcd", ["(3) etcdctl snapshot restore backup.db --data-dir /var/lib/etcd-new"]),
    ("note", ["(4) point the etcd static pod at the restored data-dir; restart"])],
    ["etcd IS the cluster state: back it up on a schedule and TEST the restore."])
SEQS["day37-app"] = (["you", "kubectl", "pod"], [
    ("msg", "you", "kubectl", ["(1) kubectl get pods -> CrashLoopBackOff"]),
    ("msg", "kubectl", "pod", ["(2) kubectl describe pod -> Events (image? OOM? probe?)"]),
    ("msg", "kubectl", "pod", ["(3) kubectl logs --previous -> the crash reason"]),
    ("note", ["(4) fix: image tag / env / resources / probe; re-apply"])],
    ["Order: get -> describe (events) -> logs --previous. Most answers are there."])
SEQS["day38-cp"] = (["you", "node", "kubelet"], [
    ("msg", "you", "node", ["(1) kubectl get nodes -> NotReady (or API down)"]),
    ("msg", "you", "kubelet", ["(2) systemctl status kubelet; journalctl -u kubelet"]),
    ("note", ["(3) control-plane pods are static: ls /etc/kubernetes/manifests"]),
    ("note", ["(4) crictl ps / crictl logs for apiserver|etcd|scheduler containers"])],
    ["Control-plane components are static pods; the kubelet + containerd run them."])


def emit_map(key):
    print("##### %s (cluster-map)" % key)
    for ln in cluster_map(MAPS[key]):
        print("   " + ln)
    print()


def emit_seq(key):
    actors, steps, tail = SEQS[key]
    print("##### %s (sequence)" % key)
    for ln in sequence(actors, steps, tail):
        print("   " + ln)
    print()


def main():
    if len(sys.argv) > 1:
        k = sys.argv[1]
        if k in MAPS:
            emit_map(k)
        elif k in SEQS:
            emit_seq(k)
        else:
            print("unknown key:", k)
        return
    for k in sorted(MAPS):
        emit_map(k)
    for k in sorted(SEQS):
        emit_seq(k)


if __name__ == "__main__":
    main()
