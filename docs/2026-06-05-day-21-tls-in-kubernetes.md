# Day 21 — TLS in Kubernetes

> Video: Day 21/40 — Manage TLS Certificates in a Kubernetes Cluster
> https://www.youtube.com/watch?v=LvPA-z8Xg4s
> Duration: ~24 min

## Problem & solution
Every cluster component talks to the API server over TLS and authenticates with
certificates. If you can't manage, rotate, and troubleshoot this web of certs,
components fail to connect and the cluster won't even start.

**Solution:** Run a cluster CA that signs certs for every component and user, authenticate links with mutual TLS, and identify users by cert CN/O.

## Where this fits in the cluster
The same cluster entities appear in every day's notes; the `<==` marks what this day touches.

```
   +----------------------------- CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+ |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | | |
   | | +------------+   +------+   +-----------+   +----------------+ | |
   | | api-server  <== every component authenticates with a cert      | |
   | | etcd  <== TLS + peer certs; holds all Secrets                  | |
   | +----------------------------------------------------------------+ |
   | +----- WORKER NODE   (kubelet | kube-proxy | runtime) ------+      |
   | |    <== kubelet has a client cert signed by the cluster CA |      |
   | | + namespace: default +                                    |      |
   | | | +----- POD -----+  |                                    |      |
   | | | | + CONTAINER + |  |                                    |      |
   | | | | | app       | |  |                                    |      |
   | | | | +-----------+ |  |                                    |      |
   | | | +---------------+  |                                    |      |
   | | +--------------------+                                    |      |
   | +-----------------------------------------------------------+      |
   +--------------------------------------------------------------------+
```

## Why a cluster is full of certificates
Every component talks to the API server over TLS, and they **authenticate each
other with certificates**. The control plane is essentially a web of
client/server cert relationships.

```
                 +------------------+
   kubectl ----> |                  | <---- kubelet (each node)
   user cert     |   kube-apiserver | <---- controller-manager
                 |  (server + client|       scheduler
   etcd <------> |   to etcd/kubelet)|
   (server cert) +------------------+
```

## The cluster's TLS web (every arrow is a cert)
Picture the whole cluster as a mesh of TLS links. **Every** arrow below is a
connection authenticated by a certificate the cluster **CA** signed; many are
mutual (both sides present a cert).

```
   USERS                       CONTROL PLANE                      NODES
   kubectl --client cert---->  +----------------+  <--client cert-- kubelet
   (CN=user, O=group)          |                |  (system:nodes)
                               | kube-apiserver |  --client cert-->  kubelet
   controller-manager --cc-->  |  (server cert  |       (exec / logs / metrics)
   scheduler          --cc-->  |   to everyone) |
   kube-proxy         --cc-->  +----------------+
                                  |        ^
                     client cert  |        |  server + peer certs
                                  v        |
                               +----------------+
                               |     etcd       |   <== holds ALL state + Secrets
                               +----------------+
```

> Two takeaways: (1) the **CA is the root of all trust** — whoever holds
> `ca.key` can mint any identity; (2) the api-server is both a **server** (to
> kubectl/kubelet) and a **client** (to etcd/kubelet).

## Where certs live (control plane)
On a kubeadm cluster the control-plane certificates live in a well-known
directory, with your own client credentials in the kubeconfig.

```
   /etc/kubernetes/pki/
     ca.crt / ca.key            -> the cluster CA (signs everything)
     apiserver.crt/.key         -> API server's SERVER cert
     apiserver-kubelet-client.* -> API server as CLIENT to kubelets
     etcd/                      -> etcd server + peer certs
   ~/.kube/config               -> your user client cert/key (or token)
```

## Client-server model
Every TLS link has two roles. A component can be **both** depending on direction:
```
   kube-apiserver  is a SERVER to kubectl/kubelet...
                   and a CLIENT when it calls etcd / kubelet.
```

## The CSR API: how a new user gets a cert
Kubernetes can act as the CA via the **CertificateSigningRequest** object.

```
   +---------+        +------------+        +----+
   | kubectl |        | api-server |        | CA |
   +---------+        +------------+        +----+
        |                    |                 |
        | (1) submit CertificateSigningRequest (CN=amy/O=devs)
        |------------------->|                 |
        |                    |                 |
     (2) admin reviews the subject and APPROVES|
        |                    |                 |
        |                    | (3) hand approved CSR to the cluster CA
        |                    |---------------->|
        |                    |                 |
        |                    | (4) CA signs -> certificate
        |                    |<----------------|
        |                    |                 |
        | (5) download signed cert -> kubeconfig
        |<-------------------|                 |
        |                    |                 |
   RESULT: amy authenticates as user=amy, group=devs; RBAC decides her powers.
```

## Generate a key and CSR
The user starts locally with openssl, creating a private key and a CSR whose
**CN** becomes their Kubernetes username.

```bash
# private key
openssl genrsa -out adam.key 2048

# certificate signing request (CN becomes the username)
openssl req -new -key adam.key -out adam.csr -subj "/CN=adam"
```

### CN = user, O = group (this is how RBAC sees you)
The api-server derives your **identity** straight from the client cert's
subject: `CN` is the username, each `O` is a group. RBAC then matches bindings
against those.

```
   subject /CN=adam/O=developers/O=oncall
        -> username: adam
        -> groups:   developers, oncall

   DANGER: /O=system:masters  is bound to cluster-admin by default
           -> a cert with that group = full control. Never sign one casually.
```

## Submit it to Kubernetes
The CSR is wrapped in a **CertificateSigningRequest** object and posted to the
API server for an admin to act on.

```yaml
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: adam
spec:
  request: <base64 of adam.csr>          # cat adam.csr | base64 | tr -d '\n'
  signerName: kubernetes.io/kube-apiserver-client
  usages:
    - client auth
```

## Approve / deny and fetch the cert
Once an admin approves the request, the cluster CA signs it and you extract the
signed certificate from the object's status.

```bash
kubectl get csr
kubectl certificate approve adam        # admin approves
kubectl certificate deny adam           # or reject

# pull the signed cert out (it's base64 in .status.certificate)
kubectl get csr adam -o jsonpath='{.status.certificate}' | base64 -d > adam.crt
```

## Inspect a certificate
Decode a certificate to confirm its subject, issuer, and validity dates.

```bash
openssl x509 -in adam.crt -text -noout    # CN, issuer, validity, etc.
```

## Attacker's playbook: attacking cluster TLS
The cluster's whole identity system rests on certificates and one CA key. Here
is how an attacker goes after it, and what stops them.

### Scenario 1 — stolen cluster CA key (total game over)
`ca.key` is the master key. Anyone who reads it can forge **any** identity.

```
   +----------+        +----+        +------------+
   | ATTACKER |        | CA |        | api-server |
   +----------+        +----+        +------------+
         |                |                 |
         | (1) reads /etc/kubernetes/pki/ca.key
         |--------------->|                 |
         |                |                 |
     (2) signs /CN=evil/O=system:masters  (cluster-admin group)
         |                |                 |
         | (3) connects with the forged cert|
         |--------------------------------->|
         |                |                 |
     (4) cert chains to the cluster CA -> FULL takeover, cannot be revoked
         |                |                 |
   DEFENSE: guard ca.key (root-only / HSM); if leaked, ROTATE the entire CA.
```

### Scenario 2 — stolen kubeconfig / client cert
A kubeconfig embeds a client cert+key (or token). Steal it, become that user.

```
   +----------+        +------------+
   | ATTACKER |        | api-server |
   +----------+        +------------+
         |                    |
         | (1) connects with a stolen kubeconfig / client cert
         |------------------->|
         |                    |
     (2) is accepted as that user -> can do whatever that user's RBAC allows
         (a leaked cluster-admin kubeconfig == full takeover)
         |                    |
   DEFENSE: short-lived certs, least-privilege RBAC, protect kubeconfig,
            rotate/re-issue the CA-signed cert (there is no cert blacklist).
```

### Scenario 3 — privilege escalation via CSR approval
The CSR API is a signing oracle. Approve carelessly and you hand out power.

```
   +----------+        +------------+
   | ATTACKER |        | api-server |
   +----------+        +------------+
         |                    |
         | (1) submit CSR /CN=mallory/O=system:masters
         |------------------->|
         |                    |
     (2) admin blindly runs 'kubectl certificate approve'
         |                    |
         | (3) signed admin cert returned
         |<-------------------|
         |                    |
     (4) mallory is now cluster-admin
         |                    |
   DEFENSE: READ every CSR subject; never approve O=system:masters.
```

### Scenario 4 — reading Secrets straight out of etcd
etcd holds all state, and Secrets are only base64 (not encrypted) by default.

```
   +----------+        +------+
   | ATTACKER |        | etcd |
   +----------+        +------+
         |                 |
         | (1) reaches etcd without its client cert
         |---------------->|
         |                 |
     (2) dumps every Secret in the cluster (base64, not encrypted)
         |                 |
   DEFENSE: etcd TLS + firewall to control plane only + encryption-at-rest.
```

### Scenario 5 — exposed/anonymous kubelet API (:10250)
The kubelet can run commands in pods. If it allows anonymous calls, that's RCE.

```
   +----------+        +---------+
   | ATTACKER |        | kubelet |
   +----------+        +---------+
         |                  |
         | (1) hits :10250 with anonymous auth enabled
         |----------------->|
         |                  |
     (2) exec into pods / read logs / run on the node (no creds)
         |                  |
   DEFENSE: --anonymous-auth=false + webhook authz + firewall 10250.
```

### Scenario 6 — anonymous access to the api-server
If unauthenticated requests are allowed, the gate is open before RBAC even runs.

```
   +----------+        +------------+
   | ATTACKER |        | api-server |
   +----------+        +------------+
         |                    |
         | (1) calls the API with NO credentials
         |------------------->|
         |                    |
     (2) lands as user 'system:anonymous' / group 'system:unauthenticated'
         -> dangerous ONLY if a Role/ClusterRole is bound to those names
         |                    |
   DEFENSE: --anonymous-auth=false; never bind roles to system:anonymous
            or system:unauthenticated.
```

### Attack -> defense summary
```
   ATTACK                       DEFEATED BY
   ---------------------------  ------------------------------------------
   stolen CA key                guard ca.key / external CA / rotate CA
   stolen kubeconfig            least-privilege RBAC + short-lived creds
   malicious CSR approval       review subjects; never sign O=system:masters
   etcd Secret theft            etcd TLS + firewall + encryption-at-rest
   open kubelet API             anonymous-auth=false + webhook authz + firewall
   anonymous api-server         anonymous-auth=false + RBAC
```

## Edge cases you must know
The gotchas that turn into 2 a.m. incidents.

```
   NO REVOCATION FOR CLIENT CERTS
     Kubernetes does NOT check CRL/OCSP. A signed client cert is valid until it
     EXPIRES - you cannot "revoke" it. If one is compromised:
       - strip its power via RBAC (delete the user's/group's bindings), OR
       - rotate the CA (invalidates ALL certs - very disruptive).
     -> prefer SHORT cert lifetimes; prefer tokens/OIDC you can actually revoke.

   CERT EXPIRY TAKES DOWN THE CLUSTER
     kubeadm control-plane certs default to ~1 YEAR. If they lapse, components
     can't talk to the api-server and the cluster "mysteriously" breaks.
     -> `kubeadm certs check-expiration`; renew with `kubeadm certs renew all`
        (an upgrade also renews them). The CA itself is good for ~10 years.

   MULTIPLE CAs, NOT ONE
     /etc/kubernetes/pki has separate CAs: the cluster CA, the etcd CA, and the
     front-proxy CA. Mixing them up causes confusing "x509: unknown authority".

   KUBELET TLS BOOTSTRAP + ROTATION
     new nodes use a bootstrap token to request their kubelet client cert; the
     kubelet can auto-rotate it (--rotate-certificates) before expiry.
```

## End-to-end example: provision a scoped dev user
Mint a real user `amy` in group `developers`, grant her read-only access in the
`dev` namespace, and prove she can read but not write.

```bash
# 1) key + CSR  (CN=username, O=group)
openssl genrsa -out amy.key 2048
openssl req -new -key amy.key -out amy.csr -subj "/CN=amy/O=developers"

# 2) submit a CertificateSigningRequest
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata: { name: amy }
spec:
  request: $(base64 -w0 amy.csr)
  signerName: kubernetes.io/kube-apiserver-client
  usages: ["client auth"]
  expirationSeconds: 2592000        # 30 days -> short-lived on purpose
EOF

# 3) admin reviews the subject, then approves; CA signs
kubectl get csr amy
kubectl certificate approve amy
kubectl get csr amy -o jsonpath='{.status.certificate}' | base64 -d > amy.crt

# 4) bind least-privilege RBAC (read-only in ns dev) to the USER
kubectl create rolebinding amy-view --clusterrole=view --user=amy -n dev

# 5) wire amy into a kubeconfig context and test
kubectl config set-credentials amy --client-key=amy.key \
  --client-certificate=amy.crt --embed-certs=true
kubectl config set-context amy --cluster=<cluster> --user=amy --namespace=dev
kubectl --context amy get pods         # OK (view)
kubectl --context amy run x --image=nginx   # FORBIDDEN (no create)
```

```
   amy.crt subject /CN=amy/O=developers
        -> api-server authn: user=amy, group=developers
        -> RBAC: rolebinding amy-view (clusterrole view) in ns dev
        -> can GET/LIST in dev, cannot CREATE/DELETE anywhere
```

## Debug & verify cluster certs
The commands you reach for when "x509" errors appear or access breaks.

```bash
# control-plane cert expiry at a glance
kubeadm certs check-expiration
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -subject -issuer -dates

# what cert is the api-server actually serving?
openssl s_client -connect <api-server>:6443 -showcerts </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# decode the client cert embedded in YOUR kubeconfig (who am I, when do I expire?)
kubectl config view --raw \
  -o jsonpath='{.users[0].user.client-certificate-data}' \
  | base64 -d | openssl x509 -noout -subject -dates

# what does the api-server think my identity is right now?
kubectl auth whoami
kubectl auth can-i --list

# renew everything (kubeadm) if certs are near/after expiry
kubeadm certs renew all
```

## Key takeaways
- The cluster has a **CA** (`/etc/kubernetes/pki/ca.crt`) that signs all certs;
  whoever holds **`ca.key` can mint any identity** — guard it above all else.
- Components authenticate to each other with **client/server certs** over TLS;
  the api-server is both server and client.
- New users: generate key+CSR, submit a **CertificateSigningRequest**, admin
  **approves**, CA signs, you wire it into kubeconfig.
- `CN` in the CSR = the **username**; each `O` = a **group**. `O=system:masters`
  is cluster-admin — never sign it casually.
- **Client certs can't be revoked** (no CRL/OCSP): use short lifetimes, strip
  power via RBAC, or rotate the CA. kubeadm certs expire in ~1 year.

## Checklist
- [ ] Listed the certs under `/etc/kubernetes/pki` (and the separate etcd/front-proxy CAs)
- [ ] Generated a `.key` and `.csr` with openssl
- [ ] Created a CertificateSigningRequest and approved it
- [ ] Decoded the signed cert and inspected it with `openssl x509`
- [ ] Provisioned a scoped user (CN/O) and bound least-privilege RBAC
- [ ] Checked control-plane cert expiry (`kubeadm certs check-expiration`)
- [ ] Can explain why a leaked CA key / kubeconfig is catastrophic, and the fixes
- [ ] Understand client certs can't be revoked (RBAC-strip or rotate CA instead)
