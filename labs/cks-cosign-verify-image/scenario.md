# Sign an image, and prove the signature by having another one refused

## The situation

A **local registry** runs on the node, at `localhost:5000`. It holds two
images, copied as-is from Docker Hub:

- `localhost:5000/appli/web:1.0`, the one the team wants to deploy;
- `localhost:5000/appli/outil:1.0`, some other image.

**Neither is signed.** Nothing tells an image your team built from an image a
third party pushed in its place.

`cosign` and `crane` are installed on the node.

## What you must achieve

1. A signing **key pair**, generated on the node.

2. The `appli/web:1.0` image is **signed** with the private key, and its
   signature sits in the registry, next to it.

3. The **public key** is published in the cluster, in a ConfigMap named
   `cosign-pub-key` in the `chaine-signature` namespace, under the
   `cosign.pub` key.

4. The private key **does not leave the node** and enters no cluster object.

## Useful bearings

`cosign generate-key-pair` writes two files in the current directory. The tool
asks for a password interactively; the `COSIGN_PASSWORD` environment variable
supplies it without dialogue, including empty.

Signing **pushes** the signature into the registry, in the same repository as
the image, under a tag derived from its digest. That is why this lab runs a
local registry: no public registry would accept that write without
credentials.

`crane ls <repository>` lists a repository's tags, signatures included.

`cosign verify --key <public key> <image>` returns an exit code: zero if the
signature is valid, non-zero otherwise.

## How you will know it works

The last test takes the public key **from the ConfigMap**, as a third party
would, and uses it on **both** images. It must accept the one you signed and
refuse the other. A verification that accepts everything proves nothing, and
that is the most dangerous case: a chain that accepts everything looks like a
chain that works.

```bash
dsoxlab check cks-cosign-verify-image
```
