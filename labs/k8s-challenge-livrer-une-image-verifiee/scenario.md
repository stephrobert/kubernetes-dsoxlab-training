# Let only verified images in, without guidance

## The situation

The delivery team wants the kubeadm cluster to run only images that are
**pinned**, **analysed** and **signed**. Today none of that holds. In the
**`livraison`** namespace:

- the **`vitrine`** Deployment runs `nginx:1.27-alpine`, named by its tag;
- the **`boutique`** Deployment runs `nginx:1.21`, an image from 2021;
- a **local registry** answers at `localhost:5000` on the control plane. It
  holds `localhost:5000/appli/web:1.0`, the image the team wants to deliver,
  and `localhost:5000/appli/outil:1.0`, some other image. **Neither is
  signed.**

On the node, the **`inventaire`** application has its Dockerfile in
`/root/inventaire/`. It builds and runs, and a static analysis rejects it.

`cosign`, `crane` and `trivy` are installed on the node. **Kyverno 1.19.2** is
installed in the cluster, with **no policy**: it reaches the local registry at
the same address, `localhost:5000`.

You are on the control plane, with `kubectl` and `sudo`. No procedure is
given: the module taught you what you need.

## What you must achieve

1. **`vitrine`** references its image by its **digest**, not by a tag.
2. It is still the requested image, **`nginx:1.27-alpine`**, not another
   version.
3. The declared digest is the one the **node runs**, and both replicas run.
4. The **static analysis findings** on the Dockerfile are gone, and the image
   **still does the same thing**: a Node image that runs `server.js`.
5. A **public key** is published in the cluster, in a ConfigMap named
   **`cosign-pub-key`** in `livraison`, under the **`cosign.pub`** key. The
   private key stays on the node.
6. The **signature** of `appli/web:1.0` is **pushed** to the registry, next to
   the image.
7. The published key **accepts** the signed image and **refuses** the other.
8. **`boutique`** no longer runs on its original image, and still runs nginx.
9. The new image carries **strictly fewer critical vulnerabilities** than the
   old one, measured by a **new scan**.
10. The cluster **refuses at creation** a Pod whose image from the local
    registry is **not signed**, and **accepts** the signed image.

## How you will be graded

Ten states, equally weighted. The pass mark is **70 out of 100**, and states
**3, 9 and 10** are **blocking**: an image that is really pinned, an image
that is really less exposed, and a cluster that only admits what is signed.
Passing the others does not make up for missing one of them.

The tests ask the node's runtime what runs, run the static analysis and the
vulnerability scans again, verify the signatures with the key taken from the
ConfigMap, then submit two Pods to admission without creating them. The
feedback is limited to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-livrer-une-image-verifiee
dsoxlab submit k8s-challenge-livrer-une-image-verifiee
```
