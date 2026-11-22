# Sign an image with cosign and publish its public key

The lesson shows how to generate a key pair, sign the digest of an image, find
the signature in the registry and verify it. This course shows three
situations it only mentions: a moved tag that loses its signature, an
annotation required at verification, and an image copied to another
repository that arrives without its signature.

You work in the `~/essai-cosign` folder and the `essai/` repository of the
local registry, with your own key pair. The challenge targets another image
and other keys: you will do it on your own, at the end.

Related page: [Sign and verify an image](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/signer-et-verifier-une-image/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-cosign-verify-image
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). A local registry answers at `localhost:5000`, and
`cosign` and `crane` are installed.

The outputs shown in this course were recorded on this machine on
22 November 2026.

All the signatures of this course are made **offline**: the
`sans-journal.json` configuration publishes nothing to Rekor, the public log
of Sigstore, hence `--insecure-ignore-tlog=true` at verification. That is the
method described in the troubleshooting section of the lesson. The challenge,
for its part, verifies with the default configuration of cosign, which
requires the Rekor entry: an offline signature does not pass it.

Create a key pair and the configuration without a log, then copy an image into
the test repository:

```bash
mkdir -p ~/essai-cosign && cd ~/essai-cosign && COSIGN_PASSWORD= cosign generate-key-pair >/dev/null 2>&1; cosign signing-config create --out sans-journal.json >/dev/null 2>&1; ls; crane copy localhost:5000/appli/outil:1.0 localhost:5000/essai/outil:1.0 >/dev/null 2>&1; crane digest localhost:5000/essai/outil:1.0
```

```text
cosign.key
cosign.pub
sans-journal.json
sha256:a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec
```

## 🏷️ Exercise 1: a moved tag loses its signature

Sign the test image by its digest, then verify it by its tag:

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); COSIGN_PASSWORD= cosign sign -y --key cosign.key --signing-config sans-journal.json --allow-http-registry localhost:5000/essai/outil@$D >/dev/null 2>&1; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/outil:1.0 >/dev/null 2>&1; echo "tag 1.0 : code $?"
```

```text
tag 1.0 : code 0
```

Code 0: the `1.0` tag points to the signed image. Now move that tag onto
another image, as someone pushing over it would, and verify again by the tag:

```bash
cd ~/essai-cosign && crane copy localhost:5000/appli/web:1.0 localhost:5000/essai/outil:1.0 >/dev/null 2>&1; crane digest localhost:5000/essai/outil:1.0; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/outil:1.0 2>&1 | tail -1; echo "tag 1.0 déplacé : code ${PIPESTATUS[0]}"
```

```text
sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
error during command execution: no signatures found
tag 1.0 déplacé : code 10
```

The digest changed, and verification returns code 10 (`no signatures found`).
The signature stayed attached to the old content: that is what makes it
impossible to pass an image off as another by moving a tag.

## 🔖 Exercise 2: require an annotation

A signature can carry annotations, key-value pairs that verification can
require. Sign the image stating the team that ships it, then verify with the
right value, and with another one:

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); COSIGN_PASSWORD= cosign sign -y --key cosign.key --signing-config sans-journal.json --allow-http-registry -a equipe=boutique localhost:5000/essai/outil@$D >/dev/null 2>&1; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry -a equipe=boutique localhost:5000/essai/outil@$D >/dev/null 2>&1; echo "equipe=boutique : code $?"; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry -a equipe=paiement localhost:5000/essai/outil@$D 2>&1 | tail -1; echo "equipe=paiement : code ${PIPESTATUS[0]}"
```

```text
equipe=boutique : code 0
error during command execution: no matching attestations: missing or incorrect annotation
equipe=paiement : code 1
```

With `equipe=boutique`, code 0. With `equipe=paiement`, code 1: the signature
is valid, but it does not carry the required annotation. One key can thus
serve several teams, each one deploying only what was signed for it.

## 📋 Exercise 3: a copy arrives without its signature

Copy the signed image to another repository of the same registry, then
compare the tags of both repositories:

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); crane copy localhost:5000/essai/outil@$D localhost:5000/essai/copie:1.0 >/dev/null 2>&1; crane ls localhost:5000/essai/outil; echo ---; crane ls localhost:5000/essai/copie; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/copie@$D 2>&1 | tail -1; echo "copie : code ${PIPESTATUS[0]}"
```

```text
sha256-65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
1.0
sha256-a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec
---
1.0
error during command execution: no signatures found
copie : code 10
```

The original repository holds the `sha256-...` tags of the two signatures
made in this course. The `copie` repository only has `1.0`: `crane copy`
copied the image, not the signature artifact that lives next to it.
Verification returns code 10. A verification that fails after a registry
migration often has this cause: copy the signatures too, or sign again.

## 🧹 Clean-up

Delete the test folder and its keys:

```bash
rm -rf ~/essai-cosign; ls -d ~/essai-cosign
```

```text
ls: cannot access '/home/ansible/essai-cosign': No such file or directory
```

The `essai/` repository of the registry goes away with the `reset`, which
recreates the lab registry. Leave the machine and reset the lab. `dsoxlab
reset` replays the lab's clean-up then its preparation: you get back exactly
the starting state of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-cosign-verify-image
dsoxlab check cks-cosign-verify-image
```

```text
╭─ Result: cks-cosign-verify-image ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a team image to sign, and a public key to
publish in the cluster, without the private key leaving the node.

```bash
dsoxlab run cks-cosign-verify-image
dsoxlab challenge cks-cosign-verify-image
```
