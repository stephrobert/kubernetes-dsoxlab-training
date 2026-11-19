# Challenge: Move a password out of a manifest, without the application noticing

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`paiement`** namespace, the **`passerelle`** Deployment is
running and doing its job. It receives its database password through the
**`DB_PASSWORD`** environment variable, whose value is written **in clear in
the manifest**.

That manifest is versioned, reviewed, copied into backups. Anything that can
read it can read the password, even what has no reason to know it.

## 🎯 What you must obtain

1. The password **no longer appears** in the Deployment manifest.

2. It is stored in a **Secret** of the namespace, as the value of one of its
   keys: read back and decoded, that key gives exactly the password. The names
   of the Secret and of the key are up to you.

3. The password is in clear **nowhere else** in the namespace, and in
   particular in **no ConfigMap**. Moving it to a ConfigMap would take it out
   of the manifest without protecting anything. This item is checked with the
   previous one: the value is in a Secret, *and* in no ConfigMap.

4. The application still receives its password in the **`DB_PASSWORD`**
   variable, unchanged. That variable **takes its value from the Secret**, by
   reference. It already holds the right value at the start: what is checked is
   where it comes from.

5. The same password is **also** available as a **file**, in the
   `/etc/passerelle` directory of the container. The volume must point to that
   Secret and be mounted at that exact path.

6. The Deployment is still running: the update goes all the way, and the ready
   Pod is the one **born from the changed manifest**, which mounts the Secret.
   A Pod was already running at the start, so "a Pod is running" is not enough.
   Deleting the variable would make the value disappear from the manifest, but
   that is not what is asked.

Change what exists. The Deployment is **updated in place**, keeping its name
and its history: deleting then recreating it is refused. `kubectl rollout
history` shows the difference.

## 🧭 Useful landmarks

The Secret is created in one command, without writing YAML.

It is **not encrypted**: the value is encoded in it, which lets it travel, not
protects it. What it changes is that the value no longer lives in the middle of
the application configuration.

The two injection ways asked for are not equal: an environment variable is
frozen for the whole life of the process, while a mounted file is updated when
the value changes.

Mounted as a volume, a Secret puts each key in a file **named after it**, with
no extension.

A Pod that asks for a missing Secret, or for a key that does not exist in it,
**does not start**: it stays in `CreateContainerConfigError`, and the Pod
events name what is missing.

## ✅ How you will know it is right

Nine tests, one per state asked, each worth one ninth of the grade. They read
the Deployment, the decoded Secret and the ConfigMaps of the namespace, then
they step into the container to check that the application receives its
password, through the variable and through the file. None of them passes on the
starting situation.

```bash
dsoxlab check ckad-secret-injection-protection
```
