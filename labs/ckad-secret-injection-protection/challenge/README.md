# Challenge: Rotate a leaked password and take it out of the manifest

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`paiement`** namespace, the **`passerelle`** Deployment
is running. It receives the password of its database through the
**`DATABASE_PASSWORD`** environment variable, whose value is written **in
clear text in the manifest**. This manifest was set with `kubectl apply`.

This password has **leaked**. The database team revoked it and created a new
one, which you find in the file **`~/paiement/nouveau-mot-de-passe.txt`**. It
changes each time the lab is prepared: read it from this file.

## 🎯 What you must obtain

1. The **new** password is stored in a **Secret** of the namespace, as the
   value of one of its keys: read back and decoded, this key gives exactly the
   content of the file. The name of the Secret and of the key are up to you.

2. Neither the old nor the new password appears in the manifest of the
   Deployment, as `kubectl get deployment passerelle -o yaml` returns it.

3. Neither of them is in clear text in a **ConfigMap** of the namespace.
   Moving it to a ConfigMap would take it out of the manifest without
   protecting anything.

4. The application receives the new password in the **`DATABASE_PASSWORD`**
   variable, which **takes its value from the Secret**, by reference.

5. The same password is **also** available as a **file**, in the
   `/etc/passerelle` directory of the container. The volume must name this
   Secret and be mounted at that exact path.

6. The Deployment still runs: the update completes, and the ready Pod is the
   one **born from the modified manifest**, which mounts the Secret.

Change what exists. The Deployment is **updated in place**, with its name and
its history: deleting then recreating it is refused.

## 🧭 Useful landmarks

Create the Secret from the file: the password then goes neither through a
command nor into the shell history. The file has no final line break.

`kubectl apply` keeps a copy of the applied manifest in an annotation of the
Deployment. Depending on how you change the Deployment, this copy follows or
does not: read the whole manifest again after your change.

A Pod that asks for a missing Secret, or for a key that does not exist in it,
**does not start**: it stays in `CreateContainerConfigError`, and the events of
the Pod name what is missing.

## ✅ How you will know it is right

Nine tests, one per requested state. They read the Deployment, the decoded
Secret and the ConfigMaps of the namespace, then they enter the container to
check that the application receives the new password, through the variable and
through the file. None passes on the starting situation.

```bash
dsoxlab check ckad-secret-injection-protection
```
