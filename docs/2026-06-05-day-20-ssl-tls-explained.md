# Day 20 — SSL/TLS Explained Simply

> Video: Day 20/40 — SSL/TLS Explained Simply
> https://www.youtube.com/watch?v=njT5ECuwCTo
> Duration: ~13 min

## Key terms
| Term | Meaning |
| --- | --- |
| TLS | Encrypts and authenticates a connection (formerly SSL) |
| Symmetric | One shared key for bulk encryption |
| Asymmetric | A public/private key pair |
| CA | Certificate Authority that signs certificates |
| Certificate | Signed binding of an identity to a public key |
| Handshake | Negotiation that sets up the secure session |
| mTLS | Mutual TLS — both sides present a certificate |
| SNI | Hostname sent so the server picks the right cert |
| CN / SAN | Common Name / Subject Alternative Names a cert covers |

## Problem & solution
On a plain HTTP connection anyone on the network path can read traffic, tamper
with it, or impersonate the server. We need confidentiality, integrity, and
authenticity, which is exactly what TLS provides.

**Solution:** Use hybrid encryption: asymmetric keys to exchange a session key and verify a CA-signed certificate, then fast symmetric encryption, giving confidentiality, integrity, and authenticity.

## Where this fits in the cluster
TLS is not a single layer — it secures connections **at every level** of
Kubernetes, from external traffic down to control-plane internals.

```
   +------------------------------ CLUSTER ------------------------------+
   | +------------------------ CONTROL PLANE -------------------------+  |
   | | +------------+   +------+   +-----------+   +----------------+ |  |
   | | | api-server |   | etcd |   | scheduler |   | controller-mgr | |  |
   | | +------------+   +------+   +-----------+   +----------------+ |  |
   | | api-server  <== serves HTTPS; verifies client certs            |  |
   | | etcd  <== TLS to etcd; encrypted at rest                       |  |
   | +----------------------------------------------------------------+  |
   | +-------- WORKER NODE   (kubelet | kube-proxy | runtime) ---------+ |
   | |    <== kubelet uses certs to talk to the api-server             | |
   | | +-------------------- namespace: default ---------------------+ | |
   | | | +-------------------------- POD --------------------------+ | | |
   | | | | +--------------------- CONTAINER ---------------------+ | | | |
   | | | | | app                                                 | | | | |
   | | | | |    <== app may do its own TLS / mTLS (service mesh) | | | | |
   | | | | +-----------------------------------------------------+ | | | |
   | | | +---------------------------------------------------------+ | | |
   | | +-------------------------------------------------------------+ | |
   | +-----------------------------------------------------------------+ |
   +---------------------------------------------------------------------+
```

## The problem TLS solves
On a plain HTTP connection anyone on the path (Wi-Fi, ISP, proxy) can **read and
tamper** with traffic. TLS gives us three guarantees:

```
   Confidentiality -> nobody else can read it (encryption)
   Integrity       -> nobody can change it undetected
   Authenticity    -> you are really talking to who you think (certs)
```

## Symmetric vs Asymmetric encryption
The two families of encryption trade off speed against the problem of how to
share keys safely.

```
   SYMMETRIC                         ASYMMETRIC
   one shared secret key             a key PAIR: public + private
   encrypt + decrypt with same key   encrypt with one, decrypt with the other
   fast                              slow
   problem: how to share the key     solves the key-sharing problem
            safely over the network?
```

> Public key encrypts -> only the matching private key decrypts (and vice-versa).
> The private key NEVER leaves the server.

## TLS uses BOTH (hybrid)
Asymmetric is used only to **safely agree on a symmetric key**, then the fast
symmetric key encrypts the actual data.

```
   1. Client gets server's PUBLIC key (from its certificate)
   2. Client + server use it to securely exchange a SESSION key (symmetric)
   3. All further traffic is encrypted with the fast SESSION key
```

## Why we need a Certificate Authority (CA)
A public key alone proves nothing — an attacker could hand you THEIR key.
A **certificate** binds a public key to an identity, signed by a trusted **CA**.

```
   Server -> generates key pair, creates a CSR (Certificate Signing Request)
   CA     -> verifies identity, SIGNS it -> issues a certificate
   Client -> trusts the CA, so it trusts any cert the CA signed
```

```
   +-----------+        CSR        +-----------+
   |  Server   | ----------------> |    CA     |
   | (pub key) | <---------------- | (signs)   |
   +-----------+   signed cert     +-----------+
        |
        | presents signed cert
        v
   +-----------+
   |  Client   |  trusts CA -> trusts the cert
   +-----------+
```

## The TLS handshake (simplified)
The handshake is the opening exchange where the two sides agree on ciphers,
verify the server's certificate, and establish the shared session key.

```
   Client  --- hello (supported ciphers) ----------->  Server
   Client  <-- hello + CERTIFICATE (public key) -----  Server
   Client  --- verifies cert against trusted CA
   Client  --- agrees on a session key (using pub key)-> Server
   Both    === switch to symmetric SESSION key =====
   ......... encrypted application data flows .........
```

## The certificate chain (root -> intermediate -> leaf)
Real certs are not signed directly by a root. A root CA signs **intermediates**,
which sign your **leaf** (server) cert. The client trusts the root and walks the
chain up to it.

```
   Root CA          self-signed, lives in OS/browser TRUST STORE
      |  signs
   Intermediate CA  issued by the root (the CA's working key)
      |  signs
   Leaf cert        your server: CN/SAN = myapp.example.com

   Server MUST send: leaf + intermediate(s)   (root is NOT sent)
   Client: builds chain leaf -> intermediate -> trusted root  = VALID
```

> Classic bug: you install only the leaf and forget the intermediate. Browsers
> may still work (they cache intermediates) but `curl`/Go/Java fail with
> **"unable to get local issuer certificate"**. Always serve the **full chain**
> (`fullchain.pem`), not just the leaf.

## Mutual TLS (mTLS): both sides present a cert
Normal TLS authenticates only the **server**. With **mTLS** the client also
presents a certificate, so each side proves who it is — the basis of zero-trust
and service meshes.

```
   Normal TLS (server auth only)        mTLS (mutual auth)
   client verifies SERVER cert          client verifies SERVER cert
   server trusts anyone                 server ALSO verifies CLIENT cert
                                         both must be signed by a trusted CA

   Used by: service meshes (Istio/Linkerd), kubelet <-> api-server,
            machine-to-machine APIs, "zero-trust" internal traffic.
```

## SNI: many HTTPS sites on one IP
One load balancer / IP can host many TLS domains. The client puts the hostname
in the **ClientHello (SNI extension)** so the server knows **which certificate**
to send — before encryption is set up.

```
   ClientHello { server_name: shop.example.com }   <-- SNI (sent in the clear)
        |
        v
   server has certs for shop.example.com, blog.example.com, api.example.com
   -> picks the shop cert and continues the handshake
   Without SNI the server couldn't choose -> wrong cert / handshake failure.
```

## What a cert actually covers (CN vs SAN, wildcards)
A cert is only valid for the names listed in it. Modern clients ignore the
legacy `CN` and check the **Subject Alternative Names (SAN)** list.

```
   SAN: DNS:myapp.example.com, DNS:www.myapp.example.com
        -> valid for those exact names only

   Wildcard *.example.com
        matches:      a.example.com, b.example.com
        does NOT match: example.com (apex) or a.b.example.com (two levels)
```

## Attacker's playbook: what TLS stops (and what it doesn't)
Think like the attacker sitting on the network path (coffee-shop Wi-Fi, a
compromised router, a malicious ISP). Each move below is a real attack; TLS
defeats most of them, and the few it can't are worth knowing.

### The core threat: man-in-the-middle (MITM)
Every attack starts the same way — the attacker gets *between* you and the
server. On plain HTTP that is game over; TLS is what makes the position useless.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) request      |                  |
        |----------------->|                  |
        |                  |                  |
        |                  | (2) forwards     |
        |                  |----------------->|
        |                  |                  |
        |                  | (3) response     |
        |                  |<-----------------|
        |                  |                  |
        | (4) forwards     |                  |
        |<-----------------|                  |
        |                  |                  |
     HTTP : attacker READS + REWRITES everything (total compromise)
     HTTPS: attacker sees only ciphertext + must impersonate server
        |                  |                  |
   STOPPED BY: getting in the middle is easy; TLS makes the position useless.
```

### Scenario 1 — passive eavesdropping (sniffing Wi-Fi)
Attacker just listens. The whole defense here is encryption.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) login: password=hunter2         |
        |------------------------------------>|
        |                  |                  |
     (2) ATTACKER copies the bytes off the wire
        |                  |                  |
     PLAIN HTTP -> reads "password=hunter2"   |
     WITH TLS   -> reads "9f#$%enc%$#a1"  (useless)
        |                  |                  |
   STOPPED BY: Confidentiality (the symmetric session key).
```

### Scenario 2 — active impersonation (fake server cert)
Attacker answers as if it were the bank, handing you a cert it made. This is the
attack the CA system exists to stop.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) ClientHello  |                  |
        |----------------->|                  |
        |                  |                  |
        | (2) cert CN=bank.com, signed by EvilCA
        |<-----------------|                  |
        |                  |                  |
     (3) CLIENT: is EvilCA in my trust store? -> NO
         -> warning / connection ABORTED (real SERVER never reached)
        |                  |                  |
   STOPPED BY: Authenticity (cert must chain to a CA you already trust).
```

### Scenario 3 — tampering / injection
Attacker flips bytes in flight to change the message.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) transfer $10 |                  |
        |----------------->|                  |
        |                  |                  |
        |                  | (2) edited -> transfer $9999
        |                  |----------------->|
        |                  |                  |
     (3) SERVER checks the TLS record auth tag (AEAD/MAC)
         -> tag mismatch -> record DROPPED    |
        |                  |                  |
   STOPPED BY: Integrity (per-record authentication).
```

### Scenario 4 — SSL stripping (downgrade HTTPS -> HTTP)
Attacker doesn't break TLS — it keeps you from ever starting it. You type
`bank.com`, the first request is HTTP, and the attacker quietly proxies.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) HTTP (no TLS yet)               |
        |----------------->|                  |
        |                  |                  |
        |                  | (2) HTTPS (real TLS here only)
        |                  |----------------->|
        |                  |                  |
        |                  | (3) HTTPS response
        |                  |<-----------------|
        |                  |                  |
        | (4) HTTP (plaintext)                |
        |<-----------------|                  |
        |                  |                  |
     CLIENT never upgraded to HTTPS -> steps 1 & 4 are readable
        |                  |                  |
   STOPPED BY: HSTS (browser refuses HTTP) + redirects + preload list.
```

### Scenario 5 — protocol / cipher downgrade
Attacker tampers with the handshake to force a weak, breakable cipher.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) ClientHello: |                  |
        | TLS1.3 + strong ciphers             |
        |----------------->|                  |
        |                  |                  |
        |                  | (2) REWRITES ->  |
        |                  | "only TLS1.0 / export cipher"
        |                  |----------------->|
        |                  |                  |
        | (3) ServerHello + Finished          |
        | (MAC over whole handshake)          |
        |<------------------------------------|
        |                  |                  |
     (4) CLIENT verifies the Finished MAC -> handshake was tampered
         -> ABORT. No weak cipher is ever used.
        |                  |                  |
   STOPPED BY: downgrade protection (Finished MAC); disable old TLS;
               TLS 1.3 removes weak/export ciphers entirely.
```

### Scenario 6 — replay attack
Attacker records a valid encrypted request and re-sends it later.

```
   +--------+        +----------+        +--------+
   | CLIENT |        | ATTACKER |        | SERVER |
   +--------+        +----------+        +--------+
        |                  |                  |
        | (1) [encrypted POST /pay]           |
        |----------------->|                  |
        |                  |                  |
     (2) ATTACKER records the encrypted bytes |
        |                  |                  |
        |                  | (3) re-sends them tomorrow
        |                  |----------------->|
        |                  |                  |
     (4) SERVER: session keys + sequence numbers differ -> REJECT
        |                  |                  |
   STOPPED BY: per-session keys + record sequence numbers.
   CAVEAT: TLS 1.3 0-RTT early data IS replayable -> never for writes/payments.
```

### Scenario 7 — stolen private key + forward secrecy
The real nightmare: the attacker steals the server's private `.key`. What they
can do depends on whether **forward secrecy** was used.

```
   +----------+        +--------+
   | ATTACKER |        | SERVER |
   +----------+        +--------+
         |                  |
         | (1) steals the server's private .key
         |----------------->|
         |                  |
     (2) ATTACKER also recorded CLIENT<->SERVER traffic earlier.
         Can it decrypt that PAST traffic now?
         NO forward secrecy : derived from long-term key -> YES (all past)
         WITH FS (ECDHE)    : ephemeral per-session key -> NO
         |                  |
   STOPPED/LIMITED BY: ECDHE forward secrecy + key rotation + fast revocation.
```

### Scenario 8 — rogue or compromised CA (mis-issuance)
TLS trust is only as strong as the CAs you trust. If any trusted CA is tricked
or hacked into signing a cert for your domain, a MITM suddenly "works".

```
   +----------+        +----+        +--------+
   | ATTACKER |        | CA |        | CLIENT |
   +----------+        +----+        +--------+
         |                |               |
         | (1) tricks / hacks the CA      |
         |--------------->|               |
         |                |               |
         | (2) mis-issues a cert for bank.com
         |<---------------|               |
         |                |               |
         | (3) MITM presents that "valid" cert
         |------------------------------->|
         |                |               |
     (4) CLIENT: chain is valid -> ACCEPTS the fake (authenticity bypassed!)
         |                |               |
   DEFENSES: Certificate Transparency logs + CAA records + public-key pinning.
```

### Scenario 9 — domain-validation hijack (fraudulent issuance)
Attacker briefly hijacks DNS/BGP to pass an automated CA challenge and get a
*genuine* cert for a domain they don't own.

```
   +----------+        +----+
   | ATTACKER |        | CA |
   +----------+        +----+
         |                |
         | (1) hijacks DNS/BGP for the victim domain
         |--------------->|
         |                |
         | (2) ACME http-01/dns-01 challenge
         |<---------------|
         |                |
         | (3) passes it (controls the domain right now)
         |--------------->|
         |                |
     (4) CA issues a REAL, valid cert for a domain attacker doesn't own
         |                |
   DEFENSES: DNSSEC + CAA records + monitor CT logs for surprise issuance.
```

### Attack -> defense summary
```
   ATTACK                      DEFEATED BY
   ---------------------------  ------------------------------------------
   eavesdropping               confidentiality (session encryption)
   server impersonation        authenticity (CA-signed cert + trust store)
   tampering / injection       integrity (AEAD/MAC per record)
   SSL stripping               HSTS + preload + HTTPS redirect
   protocol/cipher downgrade   handshake downgrade protection / TLS 1.3
   replay                      per-session keys + sequence numbers
   stolen key (past traffic)   forward secrecy (ECDHE) + rotation + revoke
   rogue CA mis-issuance       CT logs + CAA + key pinning
```

### What TLS does NOT protect
TLS secures the **pipe**, not the endpoints. Don't over-trust the padlock.

```
   x  a compromised client/server (malware, stolen data at rest)
   x  a phishing site with its OWN valid cert (padlock != trustworthy site)
   x  traffic metadata: which host (SNI/DNS), packet sizes, timing
   x  bugs above TLS (SQLi, XSS, auth flaws) and server-side breaches
   x  a user who clicks "proceed anyway" past a cert warning
```

## Keys & files you will keep seeing
These are the file types you encounter when working with TLS, each holding a
different piece of the key/certificate flow.

```
   .key  -> PRIVATE key   (keep secret, never share)
   .csr  -> Certificate Signing Request (sent to the CA)
   .crt  -> signed public CERTIFICATE (safe to share)
   ca.crt-> the CA's certificate (used to verify others)
```

## End-to-end example: HTTPS for an app via Ingress
Generate a cert, store it as a **TLS Secret**, and have an Ingress terminate
HTTPS for your service — the most common place you meet TLS in Kubernetes.

```
   client --HTTPS--> Ingress (uses tls Secret) --HTTP--> Service --> Pods
                       ^ presents the .crt, holds the .key
```

```bash
# 1) self-signed cert + key (use a real CA / cert-manager in prod)
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout tls.key -out tls.crt -subj "/CN=myapp.example.com"

# 2) store both in a kubernetes.io/tls Secret
kubectl create secret tls myapp-tls --cert=tls.crt --key=tls.key

# 3) apply the Ingress below, then test
kubectl apply -f ingress.yaml
curl -k https://myapp.example.com/        # -k since the cert is self-signed
```

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: { name: myapp }
spec:
  tls:
    - hosts: ["myapp.example.com"]
      secretName: myapp-tls           # the cert/key Secret created above
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: myapp, port: { number: 80 } }
```

> In production, let **cert-manager** issue and auto-renew certs from a CA like
> Let's Encrypt instead of self-signing — same TLS Secret, no manual openssl.

## TLS in Kubernetes: termination vs re-encrypt vs passthrough
Where TLS is *decrypted* changes the security and config. Three common modes:

```
   TERMINATION (most common): edge decrypts, plain HTTP inside the cluster
     client --HTTPS--> Ingress/LB --HTTP--> pod      (cert in a TLS Secret)

   RE-ENCRYPT: edge decrypts to inspect/route, then re-encrypts to the backend
     client --HTTPS--> Ingress --HTTPS--> pod         (two certs involved)

   PASSTHROUGH: edge forwards encrypted bytes untouched; the POD terminates TLS
     client --HTTPS---------------------> pod         (cert lives in the pod)
```

> Termination is simplest and lets the Ingress route by path/host. Passthrough
> is needed when the backend must see the raw TLS (e.g. client-cert mTLS to the
> app, or non-HTTP TLS). Re-encrypt keeps traffic encrypted end-to-end while
> still routing at the edge.

## Use cases: where you actually meet TLS
TLS shows up far beyond the browser padlock.

```
   * Public website / API   -> HTTPS via Ingress + cert-manager (Let's Encrypt)
   * Cluster internals      -> api-server, etcd, kubelet all use certs (Day 21)
   * Service-to-service      -> mesh mTLS (Istio/Linkerd) encrypts pod traffic
   * Webhooks / admission     -> api-server calls your webhook over TLS only
   * Private/internal CA      -> company root CA signs internal service certs
   * Database / broker        -> Postgres, Kafka, Redis offer TLS client conns
   * Egress to 3rd parties     -> your app verifies THEIR cert when calling out
```

## Edge cases & common errors (and the fix)
Almost every "TLS broken" ticket is one of these. Symptom -> cause -> fix:

```
   EXPIRED CERT
     symptom: "certificate has expired" / browser red page
     cause:   validity window passed
     fix:     renew (cert-manager auto-renews ~30d before expiry)

   HOSTNAME / SAN MISMATCH
     symptom: "doesn't match" / NET::ERR_CERT_COMMON_NAME_INVALID
     cause:   you hit api.example.com but cert SAN only lists www.example.com
     fix:     reissue cert with the right SAN(s) or a wildcard

   UNTRUSTED / SELF-SIGNED CA
     symptom: "self signed certificate" / "unable to verify"
     cause:   client doesn't trust the signer (self-signed or private CA)
     fix:     use a public CA, OR add the CA to the client trust store (ca.crt)

   MISSING INTERMEDIATE
     symptom: works in browser, fails in curl/Go/Java ("local issuer")
     cause:   server sent only the leaf, not the full chain
     fix:     serve fullchain (leaf + intermediates)

   KEY / CERT MISMATCH
     symptom: "key values mismatch" on load; TLS won't start
     cause:   the .key doesn't pair with the .crt
     fix:     ensure their public moduli match (see verify commands below)

   CLOCK SKEW
     symptom: "certificate is not yet valid" / expired on a fresh cert
     cause:   client/server clock is wrong
     fix:     sync time (NTP)

   PROTOCOL / CIPHER MISMATCH
     symptom: "no protocols available" / handshake_failure
     cause:   client wants TLS1.0/old cipher the server disabled
     fix:     update client, or (carefully) align supported versions

   WRONG SNI / NO SNI
     symptom: server returns the DEFAULT cert -> name mismatch
     cause:   client didn't send SNI, or sent the wrong host
     fix:     send the correct servername (curl --resolve / -servername)

   MIXED CONTENT / REDIRECT LOOP
     symptom: infinite https<->http redirects behind a terminating LB
     cause:   app forces HTTPS but LB already terminated -> sees HTTP
     fix:     honor X-Forwarded-Proto instead of the local scheme
```

## Verify & debug certificates
The openssl/kubectl commands you reach for when a cert misbehaves.

```bash
# inspect a cert: subject, issuer, SANs, validity
openssl x509 -in tls.crt -noout -text
openssl x509 -in tls.crt -noout -subject -issuer -dates    # quick expiry check

# see what a live server actually serves (chain + SNI)
openssl s_client -connect myapp.example.com:443 -servername myapp.example.com </dev/null

# verify a cert against a CA (chain validity)
openssl verify -CAfile ca.crt tls.crt

# confirm key + cert are a matching pair (these two hashes MUST be equal)
openssl x509 -noout -modulus -in tls.crt | openssl md5
openssl rsa  -noout -modulus -in tls.key | openssl md5

# in-cluster: read the cert out of a TLS Secret and check its dates
kubectl get secret myapp-tls -o jsonpath='{.data.tls\.crt}' | base64 -d \
  | openssl x509 -noout -subject -dates
```

## Key takeaways
- TLS = confidentiality + integrity + authenticity.
- **Asymmetric** to exchange a key, **symmetric** for the actual data (hybrid).
- A **CA signs certificates** so clients can trust a server's public key.
- Private key is secret; the certificate (public) is shared.
- Serve the **full chain** (leaf + intermediates); clients check **SAN**, not CN.
- **mTLS** authenticates both sides; **SNI** lets one IP serve many cert domains.
- Most TLS outages are: expired, SAN mismatch, untrusted CA, or missing
  intermediate — all checkable with `openssl x509`/`s_client`.
- TLS beats eavesdropping, tampering, and impersonation; **HSTS** stops SSL
  stripping and **forward secrecy (ECDHE)** protects past traffic if a key leaks.
- TLS secures the pipe, not the endpoints: phishing sites can hold valid certs,
  and metadata (SNI/DNS, sizes) still leaks.

## Checklist
- [ ] Can explain symmetric vs asymmetric and why TLS uses both
- [ ] Understand the CSR -> CA -> signed cert flow
- [ ] Know what `.key`, `.csr`, `.crt`, `ca.crt` each are
- [ ] Can walk through a TLS handshake at a high level
- [ ] Can explain the cert chain and why a missing intermediate breaks clients
- [ ] Understand mTLS, SNI, and SAN/wildcard matching
- [ ] Know termination vs re-encrypt vs passthrough in Kubernetes
- [ ] Can diagnose expired / SAN-mismatch / untrusted-CA with `openssl`
- [ ] Can walk an attacker through MITM, eavesdrop, tamper, SSL-strip and name
      the TLS guarantee that defeats each
- [ ] Can explain forward secrecy and why it limits a stolen-key breach
- [ ] Know what TLS does NOT protect (endpoints, phishing certs, metadata)
