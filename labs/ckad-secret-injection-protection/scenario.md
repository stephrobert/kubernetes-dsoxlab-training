# Move a password out of a manifest, without the application noticing

## The situation

In the **`paiement`** namespace, the **`passerelle`** Deployment runs and does its
job. It receives its database password through a **`DB_PASSWORD`** environment
variable, whose value is written **in the clear inside the manifest**.

That manifest is versioned, reviewed, copied into backups. Anything that can
read it can read the password, including things with no reason to know it.

## What you must achieve

1. The password value **no longer appears** in the Deployment manifest.

2. It is carried by a dedicated object in the namespace.

3. The application still receives its password in the **`DB_PASSWORD`**
   variable, unchanged.

4. The same value is **also** available as a **file**, in the container's
   `/etc/passerelle` directory.

5. The Deployment keeps running. Deleting the variable would be one way to make
   the value disappear from the manifest, but not the one you are asked for.

Modify what exists, do not replace the Deployment with an object under another
name.

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

The last test exercises **both sides**: it checks the value left the manifest,
then that it reaches the container anyway, through the variable and through the
file. Separated, these two halves would measure nothing: deleting the variable
would pass the first while breaking the application, and the second is already
true before you intervene.

```bash
dsoxlab check ckad-secret-injection-protection
```
