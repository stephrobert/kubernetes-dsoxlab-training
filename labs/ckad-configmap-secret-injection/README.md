# Give credentials to an application with a Secret

A password must not be written in a Pod manifest: that manifest is versioned,
reviewed, copied. Kubernetes keeps sensitive values in a separate object, the
**Secret**. The Pod only holds a **reference** to it, and the value only shows
up inside the container, as an environment variable or as a file. In this
course, you create Secrets, you read them, you give them to an application in
three ways, and you check what the Pod manifest really contains.

You work in a scratch namespace, `essai-secret`, with a `courrier` application
that needs credentials to send e-mails. The challenge will ask you to configure
another application: you will do it on your own, at the end.

Related page: [Kubernetes Secrets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-configmap-secret-injection
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a Secret from values

Create the scratch namespace, then a Secret `smtp-identifiants` with two values.
The `generic` type is the ordinary Secret, which stores `key=value` pairs:

```bash
kubectl create namespace essai-secret
kubectl create secret generic smtp-identifiants --from-literal=SMTP_USER=courrier --from-literal=SMTP_PASSWORD='Pluie-2026' -n essai-secret
kubectl get secret smtp-identifiants -n essai-secret
```

```text
namespace/essai-secret created
secret/smtp-identifiants created
NAME                TYPE     DATA   AGE
smtp-identifiants   Opaque   2      0s
```

`Opaque` is the technical name of the `generic` type, and `DATA 2` counts its
two keys. `describe` lists them without showing their value, only their size:

```bash
kubectl describe secret smtp-identifiants -n essai-secret | sed -n '/^Data/,$p'
```

```text
Data
====
SMTP_PASSWORD:  10 bytes
SMTP_USER:      8 bytes
```

## 📚 Exercise 2: read and decode a value

`describe` hides the values, but they remain readable by anyone allowed to read
the Secret:

```bash
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data}{"\n"}'
```

```text
{"SMTP_PASSWORD":"UGx1aWUtMjAyNg==","SMTP_USER":"Y291cnJpZXI="}
```

The values are **base64-encoded**, a simple transformation, not encryption.
`base64 -d` gives them back in clear (the `echo` adds the line break):

```bash
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data.SMTP_PASSWORD}' | base64 -d; echo
```

```text
Pluie-2026
```

A Secret therefore protects a value because it lives **apart**, with access
rights that can be restricted, not because it would be unreadable.

## 📚 Exercise 3: a Secret from a file

Like a ConfigMap, a Secret can hold a whole file. The file name becomes the
key:

```bash
printf 'serveur=smtp.exemple.fr\nport=587\n' > ~/relais.conf; kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret
kubectl get secret smtp-relais -n essai-secret -o jsonpath='{.data}{"\n"}'
```

```text
secret/smtp-relais created
{"relais.conf":"c2VydmV1cj1zbXRwLmV4ZW1wbGUuZnIKcG9ydD01ODcK"}
```

## 📚 Exercise 4: inject one key, or all of them at once

The `courrier` Pod receives the Secrets in three ways:

- `env` with `secretKeyRef`: **one** key, `SMTP_PASSWORD`, under the variable
  name of your choice, here `MOT_DE_PASSE`;
- `envFrom` with `secretRef`: **every** key of the Secret, each under its own
  name;
- a `secret` volume, mounted on `/etc/relais`: each key of `smtp-relais`
  becomes a file in it, readable by its owner only (`defaultMode: 0400`).

```bash
cat <<'YAML' | kubectl apply -n essai-secret -f -
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
kubectl wait --for=condition=Ready pod/courrier -n essai-secret --timeout=90s
```

```text
pod/courrier created
pod/courrier condition met
```

Read the variables from the container:

```bash
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE; echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD'
```

```text
MOT_DE_PASSE=Pluie-2026
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026
```

`MOT_DE_PASSE` comes from the key-by-key reference. `SMTP_USER` and
`SMTP_PASSWORD` come from `envFrom`, which reused the key names.

## 📚 Exercise 5: a Secret mounted as files

Look at the mounted directory (`-L` shows the real file, not the link that
Kubernetes puts in front of it):

```bash
kubectl exec courrier -n essai-secret -- ls -lL /etc/relais
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
total 4
-r--------    1 root     root            33 Nov 19 18:30 relais.conf
serveur=smtp.exemple.fr
port=587
```

The `relais.conf` file is there, decoded, with the rights `-r--------`:
readable by its owner only, as asked by `defaultMode: 0400`.

## 📚 Exercise 6: what the Pod manifest contains

The point of a Secret is to keep the value out of the manifest. Check it. Here
are the variables declared in the Pod:

```bash
kubectl get pod courrier -n essai-secret -o jsonpath='{.spec.containers[0].env}{"\n"}'
```

```text
[{"name":"MOT_DE_PASSE","valueFrom":{"secretKeyRef":{"key":"SMTP_PASSWORD","name":"smtp-identifiants"}}}]
```

A reference: a Secret name and a key name, no value. Finally, look for the
password in the whole Pod manifest:

```bash
kubectl get pod courrier -n essai-secret -o yaml | grep -c 'Pluie-2026'
```

```text
0
```

Zero occurrences. The password only exists in the Secret, and in the container
that needs it.

## 📚 Exercise 7: a key that does not exist

Create a Pod that asks for a key missing from the Secret, `SMTP_TOKEN`:

```bash
cat <<'YAML' | kubectl apply -n essai-secret -f -
apiVersion: v1
kind: Pod
metadata:
  name: cle-absente
spec:
  containers:
    - name: cle-absente
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      env:
        - name: JETON
          valueFrom:
            secretKeyRef:
              name: smtp-identifiants
              key: SMTP_TOKEN
YAML
sleep 8; kubectl get pod cle-absente -n essai-secret
```

```text
pod/cle-absente created
NAME          READY   STATUS                       RESTARTS   AGE
cle-absente   0/1     CreateContainerConfigError   0          8s
```

The container does not start. The Pod events say why:

```bash
kubectl get events -n essai-secret --field-selector involvedObject.name=cle-absente,type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON   MESSAGE
Failed   Error: couldn't find key SMTP_TOKEN in Secret essai-secret/smtp-identifiants
```

The message names the key and the Secret: check the spelling of both.

## 🧹 Clean up

Delete the work file and the scratch namespace:

```bash
rm -f ~/relais.conf; kubectl delete namespace essai-secret
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
