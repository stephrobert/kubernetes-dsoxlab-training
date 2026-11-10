# Move a password out of a manifest, without the application noticing

## The situation

In the **`paiement`** namespace, the **`passerelle`** Deployment runs and does its
job. It receives its database password through a **`DB_PASSWORD`** environment
variable, whose value is written **in the clear inside the manifest**.

That manifest is versioned, reviewed, copied into backups. Anything that can
read it can read the password, including things with no reason to know it.

## What you must achieve

1. The password value **no longer appears** in the Deployment manifest.

2. It is carried by a **Secret** of the namespace, as the content of one of its
   keys: read back and decoded, that key gives the password exactly. You choose
   the name of the Secret and of the key.

3. The password is in clear text **nowhere else** in the namespace, and in
   **no ConfigMap** in particular. Moving the value from the Deployment to a
   ConfigMap would make it leave the manifest without protecting anything.

4. The application still receives its password in the **`DB_PASSWORD`**
   variable, unchanged, and that variable **takes its value from that Secret**,
   by reference.

5. The same value is **also** available as a **file**, in the container's
   `/etc/passerelle` directory. The volume must name that Secret, and be
   mounted at that exact path.

6. The Deployment keeps running: its rollout goes through, and one up-to-date
   Pod is ready. Deleting the variable would be one way to make the value
   disappear from the manifest, but not the one you are asked for.

Modify what exists. The Deployment is **updated in place**, keeping its name
and its history: deleting it and recreating it is refused, and
`kubectl rollout history` is what shows the difference.

## Useful bearings

The object carrying a sensitive value is created in one command, without
writing YAML.

It is **not encrypted**: the value is encoded in it, which is transport and not
protection. What it changes is that the value stops living in the middle of the
application's configuration.

The two injection paths asked for are not equivalent: an environment variable
is frozen for the life of the process, while a mounted file is refreshed when
the value changes.

Mounted as a volume, that object drops each key as a file **named after it**,
with no added extension.

A Pod referencing a missing object, or a key that does not exist in it, **does
not start**: it stays in `CreateContainerConfigError`, and
`kubectl describe pod` names the missing one in its events.

## How you will know it works

**Nine tests, one per state above**, each weighing the same ninth of the mark.
Two of them are the reason the list is explicit: one reads the Secret's content
and decodes it, the other sweeps the ConfigMaps of the namespace. Together they
refuse the shortcut that would otherwise score full marks: the value moved into
a ConfigMap and injected from there, which takes it out of the manifest and
leaves it just as readable.

Deleting the variable still fails, as it always did: the tests that enter the
container prove the application receives its password, by the variable and by
the file. And the tests that read the cluster say **which** of the states is
missing, instead of stopping at the first one.

```bash
dsoxlab check ckad-secret-injection-protection
```
