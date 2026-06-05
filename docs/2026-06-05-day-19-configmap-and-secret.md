# Day 19 — ConfigMap and Secret

> Video: Day 19/40 — Kubernetes ConfigMap and Secret
> https://www.youtube.com/watch?v=Q9fHJLSyd7Q
> Duration: ~17 min

## The idea: decouple config from image
Don't bake config/credentials into images. Inject them at runtime so the **same
image** runs across dev/staging/prod.

```
   image (immutable)  +  ConfigMap (non-secret config)
                      +  Secret    (sensitive data)
                      =  configured container at runtime
```

## ConfigMap vs Secret
Both hold key/value config, but a **ConfigMap** is for non-sensitive settings
while a **Secret** is for sensitive data and is handled more carefully.

```
   ConfigMap -> plain config (URLs, flags, ports). NOT secret.
   Secret    -> sensitive data (passwords, tokens, keys).
                stored base64-encoded; can be encrypted at rest.
```
> base64 is **encoding, not encryption** — anyone can decode it. Protect Secrets
> with RBAC and encryption-at-rest.

## Two ways to consume them
A pod can read a ConfigMap or Secret either as **environment variables** or as
**files mounted** into the container.

```
   (A) Environment variables          (B) Mounted as files (volume)
   container env:                      /etc/config/
     APP_COLOR=blue                       app_color   -> "blue"
     DB_PASS=*****                         db_pass     -> "*****"
   - simple, static at start          - updates can propagate to files
```

## Create a ConfigMap
You can build a ConfigMap imperatively from literal key/values or from a file.

```bash
# from literals
kubectl create configmap app-config \
  --from-literal=APP_COLOR=blue --from-literal=APP_MODE=prod

# from a file
kubectl create configmap app-config --from-file=app.properties

kubectl get configmap app-config -o yaml
```

ConfigMap YAML:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_COLOR: blue
  APP_MODE: prod
```

## Create a Secret
A Secret is created the same way, but Kubernetes stores its values
**base64-encoded** rather than as plain text.

```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin --from-literal=DB_PASS=s3cr3t

kubectl get secret db-secret -o yaml      # values are base64
echo 'czNjcjN0' | base64 -d              # decode example
```

Secret YAML (values base64-encoded):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  DB_USER: YWRtaW4=        # echo -n admin | base64
  DB_PASS: czNjcjN0        # echo -n s3cr3t | base64
# (or use stringData: for plain text that K8s encodes for you)
```

## Consume as ENV VARS
Inject every key at once with `envFrom`, or map a single key into a named
variable with `valueFrom`.

```yaml
spec:
  containers:
    - name: app
      image: myapp
      envFrom:
        - configMapRef: { name: app-config }   # all keys as env
        - secretRef: { name: db-secret }
      # or pick one key:
      env:
        - name: APP_COLOR
          valueFrom:
            configMapKeyRef: { name: app-config, key: APP_COLOR }
        - name: DB_PASS
          valueFrom:
            secretKeyRef: { name: db-secret, key: DB_PASS }
```

## Consume as MOUNTED FILES
Mounting as a volume turns each key into a file under the mount path, which lets
updates propagate without restarting the pod.

```yaml
spec:
  containers:
    - name: app
      image: myapp
      volumeMounts:
        - name: cfg
          mountPath: /etc/config
        - name: sec
          mountPath: /etc/secret
          readOnly: true
  volumes:
    - name: cfg
      configMap: { name: app-config }
    - name: sec
      secret: { secretName: db-secret }
```
```
   /etc/config/APP_COLOR   -> file containing "blue"
   /etc/secret/DB_PASS     -> file containing "s3cr3t"
```

## env vs volume (update behavior)
The two consumption styles differ when the config changes: env vars are frozen
at start, while mounted files can refresh live.

```
   env var:  fixed at container start -> change needs pod restart
   volume:   mounted files can refresh after a ConfigMap/Secret update
             (with some kubelet sync delay)
```

## Key takeaways
- **ConfigMap = non-secret config; Secret = sensitive data** (base64, not encrypted).
- Inject via **env vars** (static) or **mounted files** (can refresh).
- Same image + different ConfigMaps/Secrets = portable across environments.

## Checklist
- [ ] Created a ConfigMap and a Secret (literals + file)
- [ ] Injected them as env vars (`envFrom` and single-key)
- [ ] Mounted them as files and read the values
- [ ] Decoded a Secret value with base64 and understand it's not encryption
