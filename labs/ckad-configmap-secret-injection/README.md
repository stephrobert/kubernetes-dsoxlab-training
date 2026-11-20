# Give credentials to an application with a Secret

A password must not be written in the manifest of a Pod: that manifest is
versioned, reviewed, copied. Kubernetes keeps sensitive values in a separate
object, the **Secret**. The Pod only holds a **reference** to it, and the
value only appears inside the container, as an environment variable or as a
file. The lesson shows how to create, read and inject a Secret. This course
gives Secrets to an application in three ways, then looks at two situations
the lesson describes without showing them: the same key provided by two
sources, and a Secret changed while the Pod is running.

You work in a scratch namespace, `essai-secret`, with a `courrier` application
that needs credentials to send e-mails. The challenge will ask you to
configure another application: you will do it on your own, at the end.

Related page: [Kubernetes Secrets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-configmap-secret-injection
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: two Secrets

Create the scratch namespace and two Secrets. The `generic` type is the
ordinary Secret:

- `smtp-identifiants` holds two values, `SMTP_USER` and `SMTP_PASSWORD`;
- `smtp-relais` holds a whole file, `relais.conf`, whose name becomes the
  key.

```bash
kubectl create namespace essai-secret
kubectl create secret generic smtp-identifiants --from-literal=SMTP_USER=courrier --from-literal=SMTP_PASSWORD='Pluie-2026' -n essai-secret
printf 'serveur=smtp.exemple.fr\nport=587\n' > ~/relais.conf
kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret
kubectl get secrets -n essai-secret
```

```text
namespace/essai-secret created
secret/smtp-identifiants created
secret/smtp-relais created
NAME                TYPE     DATA   AGE
smtp-identifiants   Opaque   2      0s
smtp-relais         Opaque   1      0s
```

`Opaque` is the technical name of the `generic` type, and the `DATA` column
counts the keys. `describe` lists them without showing their value, only
their size:

```bash
kubectl describe secret smtp-identifiants -n essai-secret | sed -n '/^Data/,$p'
```

```text
Data
====
SMTP_PASSWORD:  10 bytes
SMTP_USER:      8 bytes
```

## 📚 Exercise 2: inject one key, all keys, or a file

The `courrier` Pod receives the Secrets in three ways:

- `env` with `secretKeyRef`: **one** key, `SMTP_PASSWORD`, under the variable
  name of your choice, here `MOT_DE_PASSE`;
- `envFrom` with `secretRef`: **all** the keys of the Secret, each under its
  own name;
- a `secret` volume, mounted on `/etc/relais`: each key of `smtp-relais`
  becomes a file there, readable by its owner only (`defaultMode: 0400`).

Write the manifest in a file, then apply it:

```bash
cat > ~/courrier.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: courrier
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: courrier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "86400"]
      env:
        - name: MOT_DE_PASSE
          valueFrom:
            secretKeyRef:
              name: smtp-identifiants
              key: SMTP_PASSWORD
      envFrom:
        - secretRef:
            name: smtp-identifiants
      volumeMounts:
        - name: relais
          mountPath: /etc/relais
          readOnly: true
  volumes:
    - name: relais
      secret:
        secretName: smtp-relais
        defaultMode: 0400
YAML
kubectl apply -n essai-secret -f ~/courrier.yaml
kubectl wait --for=condition=Ready pod/courrier -n essai-secret --timeout=90s
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE; echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD'
```

```text
pod/courrier created
pod/courrier condition met
MOT_DE_PASSE=Pluie-2026
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026
```

`MOT_DE_PASSE` comes from the key-by-key reference. `SMTP_USER` and
`SMTP_PASSWORD` come from `envFrom`, which reused the names of the keys. Now
look at the mounted directory (`-L` shows the real file, not the link that
Kubernetes puts in front of it):

```bash
kubectl exec courrier -n essai-secret -- ls -lL /etc/relais
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
total 4
-r--------    1 root     root            33 Nov 20 12:19 relais.conf
serveur=smtp.exemple.fr
port=587
```

The `relais.conf` file is there, in clear text, with the `-r--------` rights:
readable by its owner only, as `defaultMode: 0400` asked.

The point of a Secret is to keep the value out of the manifest. Look for the
password in the whole manifest of the Pod:

```bash
kubectl get pod courrier -n essai-secret -o yaml | grep -c 'Pluie-2026'
```

```text
0
```

Zero occurrences: the Pod only holds references.

## 📚 Exercise 3: the same key in two sources

A Pod often receives a ConfigMap and a Secret through `envFrom`. If both have
a key with the same name, only one value reaches the container. Create a
`courrier-reglages` ConfigMap whose `SMTP_USER` key also exists in
`smtp-identifiants`, with another value:

```bash
kubectl create configmap courrier-reglages --from-literal=SMTP_USER=robot --from-literal=SMTP_PORT=587 --from-literal=PORT_SECOURS=2525 -n essai-secret
```

```text
configmap/courrier-reglages created
```

The `doublon` Pod receives the Secret then the ConfigMap through `envFrom`, in
that order. It also declares, in `env`, an `SMTP_PORT` variable filled by the
`PORT_SECOURS` key: `SMTP_PORT` therefore arrives twice, through `envFrom` and
through `env`.

```bash
cat > ~/doublon.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: doublon
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: doublon
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "86400"]
      envFrom:
        - secretRef:
            name: smtp-identifiants
        - configMapRef:
            name: courrier-reglages
      env:
        - name: SMTP_PORT
          valueFrom:
            configMapKeyRef:
              name: courrier-reglages
              key: PORT_SECOURS
YAML
kubectl apply -n essai-secret -f ~/doublon.yaml
kubectl wait --for=condition=Ready pod/doublon -n essai-secret --timeout=90s
kubectl exec doublon -n essai-secret -- sh -c 'echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD SMTP_PORT=$SMTP_PORT'
```

```text
pod/doublon created
pod/doublon condition met
SMTP_USER=robot SMTP_PASSWORD=Pluie-2026 SMTP_PORT=2525
```

Two results:

- `SMTP_USER` is `robot`, the value of the ConfigMap. In `envFrom`, the
  **last** source of the list wins;
- `SMTP_PORT` is `2525`, the value coming from `env`, not `587`. A variable of
  `env` always wins over `envFrom`.

Check the first rule by reversing the order. The variables of a Pod cannot be
changed: delete the Pod, swap the two entries of `envFrom` in the file, then
create it again. The `sed` command does the swap, and the second one shows the
result:

```bash
kubectl delete pod doublon -n essai-secret
sed -i '/secretRef:/{N;h;d};/configMapRef:/{N;G}' ~/doublon.yaml
sed -n '/envFrom/,/env:/p' ~/doublon.yaml
kubectl apply -n essai-secret -f ~/doublon.yaml
kubectl wait --for=condition=Ready pod/doublon -n essai-secret --timeout=90s
kubectl exec doublon -n essai-secret -- sh -c 'echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD SMTP_PORT=$SMTP_PORT'
```

```text
pod "doublon" deleted from essai-secret namespace
      envFrom:
        - configMapRef:
            name: courrier-reglages
        - secretRef:
            name: smtp-identifiants
      env:
pod/doublon created
pod/doublon condition met
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026 SMTP_PORT=2525
```

The Secret is now last: `SMTP_USER` is `courrier`. `SMTP_PORT` is still
`2525`, since `env` comes before `envFrom`. No error and no warning reports
these duplicates: a ConfigMap placed after a Secret can replace a credential
without anything saying so.

## 📚 Exercise 4: a Secret changed while the Pod runs

Change the password in `smtp-identifiants`, then the port in the file of
`smtp-relais`. `stringData` accepts a clear-text value, which Kubernetes
encodes itself:

```bash
kubectl patch secret smtp-identifiants -n essai-secret -p '{"stringData":{"SMTP_PASSWORD":"Neige-2027"}}'
printf 'serveur=smtp.exemple.fr\nport=465\n' > ~/relais.conf
kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret --dry-run=client -o yaml | kubectl replace -f -
```

```text
secret/smtp-identifiants patched
secret/smtp-relais replaced
```

Measure how long the mounted file takes to follow. The loop reads the file
again every 5 seconds, and stops after 36 tries, that is 3 minutes, even if
nothing changes:

```bash
debut=$SECONDS; for i in $(seq 1 36); do kubectl exec courrier -n essai-secret -- grep -q port=465 /etc/relais/relais.conf 2>/dev/null && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
attente : 81 s
serveur=smtp.exemple.fr
port=465
```

The file followed on its own, here in 81 seconds. Now read the variables of
the same Pod, then the value stored in the Secret. `base64 -d` decodes the
stored value:

```bash
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE SMTP_PASSWORD=$SMTP_PASSWORD'
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data.SMTP_PASSWORD}' | base64 -d; echo
```

```text
MOT_DE_PASSE=Pluie-2026 SMTP_PASSWORD=Pluie-2026
Neige-2027
```

The Secret says `Neige-2027`, but the container still sees `Pluie-2026`,
through both variables. A variable is read when the container starts, then
stays frozen. After a password change, an application that reads its
credentials from variables keeps the old one until its Pod is replaced.

## 🧹 Clean up

Delete the work files and the scratch namespace:

```bash
rm -f ~/relais.conf ~/courrier.yaml ~/doublon.yaml
kubectl delete namespace essai-secret
```

```text
namespace "essai-secret" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-configmap-secret-injection
dsoxlab check ckad-configmap-secret-injection
```

```text
╭─ Result: ckad-configmap-secret-injection ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/14 tests         │
╰───────────────────────────────────────────╯
```

0 out of 14: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: give an application its settings through a
ConfigMap and its credentials through a Secret, with no password in its
manifest.

```bash
dsoxlab run ckad-configmap-secret-injection
dsoxlab challenge ckad-configmap-secret-injection
```
