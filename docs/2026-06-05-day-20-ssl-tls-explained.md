# Day 20 — SSL/TLS Explained Simply

> Video: Day 20/40 — SSL/TLS Explained Simply
> https://www.youtube.com/watch?v=njT5ECuwCTo
> Duration: ~13 min

## The problem TLS solves
On a plain HTTP connection anyone on the path (Wi-Fi, ISP, proxy) can **read and
tamper** with traffic. TLS gives us three guarantees:

```
   Confidentiality -> nobody else can read it (encryption)
   Integrity       -> nobody can change it undetected
   Authenticity    -> you are really talking to who you think (certs)
```

## Symmetric vs Asymmetric encryption
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
```
   Client  --- hello (supported ciphers) ----------->  Server
   Client  <-- hello + CERTIFICATE (public key) -----  Server
   Client  --- verifies cert against trusted CA
   Client  --- agrees on a session key (using pub key)-> Server
   Both    === switch to symmetric SESSION key =====
   ......... encrypted application data flows .........
```

## Keys & files you will keep seeing
```
   .key  -> PRIVATE key   (keep secret, never share)
   .csr  -> Certificate Signing Request (sent to the CA)
   .crt  -> signed public CERTIFICATE (safe to share)
   ca.crt-> the CA's certificate (used to verify others)
```

## Key takeaways
- TLS = confidentiality + integrity + authenticity.
- **Asymmetric** to exchange a key, **symmetric** for the actual data (hybrid).
- A **CA signs certificates** so clients can trust a server's public key.
- Private key is secret; the certificate (public) is shared.

## Checklist
- [ ] Can explain symmetric vs asymmetric and why TLS uses both
- [ ] Understand the CSR -> CA -> signed cert flow
- [ ] Know what `.key`, `.csr`, `.crt`, `ca.crt` each are
- [ ] Can walk through a TLS handshake at a high level
