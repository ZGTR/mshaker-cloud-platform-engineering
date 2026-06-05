# Day 21 — TLS in Kubernetes

> Video: Day 21/40 — Manage TLS Certificates in a Kubernetes Cluster
> https://www.youtube.com/watch?v=LvPA-z8Xg4s
> Duration: ~24 min

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

## Where certs live (control plane)
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
   1. user generates a private key + CSR (openssl)
   2. submit the CSR to the cluster (CertificateSigningRequest)
   3. an admin APPROVES it
   4. cluster CA signs -> user downloads the signed cert
   5. user puts key + cert in kubeconfig
```

## Generate a key and CSR
```bash
# private key
openssl genrsa -out adam.key 2048

# certificate signing request (CN becomes the username)
openssl req -new -key adam.key -out adam.csr -subj "/CN=adam"
```

## Submit it to Kubernetes
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
```bash
kubectl get csr
kubectl certificate approve adam        # admin approves
kubectl certificate deny adam           # or reject

# pull the signed cert out (it's base64 in .status.certificate)
kubectl get csr adam -o jsonpath='{.status.certificate}' | base64 -d > adam.crt
```

## Inspect a certificate
```bash
openssl x509 -in adam.crt -text -noout    # CN, issuer, validity, etc.
```

## Key takeaways
- The cluster has a **CA** (`/etc/kubernetes/pki/ca.crt`) that signs all certs.
- Components authenticate to each other with **client/server certs** over TLS.
- New users: generate key+CSR, submit a **CertificateSigningRequest**, admin
  **approves**, CA signs, you wire it into kubeconfig.
- `CN` in the CSR = the **username** Kubernetes sees (groups via `O=`).

## Checklist
- [ ] Listed the certs under `/etc/kubernetes/pki`
- [ ] Generated a `.key` and `.csr` with openssl
- [ ] Created a CertificateSigningRequest and approved it
- [ ] Decoded the signed cert and inspected it with `openssl x509`
