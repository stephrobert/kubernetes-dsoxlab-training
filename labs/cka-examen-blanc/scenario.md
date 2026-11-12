# CKA mock exam: 17 tasks in 120 minutes

## Before you start

This exam follows the CKA format: hands-on tasks, graded on the final state of
the cluster, with no hint. **Plan for 120 minutes**, in one sitting, and start
your own timer: the tool does not. The tasks are independent, except task 9,
which requires the node of task 3 repaired.

You work on the control plane **`k8s-cp.lab`**, with `kubectl`. Your kubeconfig
holds three contexts, all pointing at the same cluster: **`cka-infra`**
(namespace `default`), **`cka-appli`** (namespace `appli`) and **`cka-reseau`**
(namespace `reseau`). **Each task starts with the context to use.** Switch
before working: a resource created in the wrong namespace does not count. The
worker **`k8s-w1.lab`** is reached with `ssh k8s-w1.lab`.

The images to use:

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The tasks

### Task 1 (5%): context `cka-infra`

Create the StorageClass **`rapide`**, served by the `rancher.io/local-path`
provisioner, which **keeps** its volumes when their claim disappears and creates
them only when a Pod uses the claim.

### Task 2 (5%): context `cka-appli`

Create the claim **`donnees`** of **100Mi**, `ReadWriteOnce`, on the class
`rapide`. The Pod **`ecrivain`** (busybox image) mounts it on **`/data`** and
writes the file **`/data/ok`** there, whose content is `ok`.

### Task 3 (10%): context `cka-infra`

The node **`k8s-w1.lab`** is `NotReady`. Bring it back into service, so that it
stays so **after a reboot**.

### Task 4 (5%): context `cka-appli`

The Deployment **`facture`** cannot start. Repair it so that its **two
replicas** are ready. It must serve nginx the way the image does on its own.

### Task 5 (10%): context `cka-appli`

The Service **`annuaire`** leads to no Pod. Repair it without touching the
Deployment `annuaire`, so that the Pod **`client`** gets the answer `annuaire`
when it queries `http://annuaire/`.

### Task 6 (5%): context `cka-appli`

Write into **`~/examen/erreurs.txt`** the log lines of the **`app`** container
of the Pod **`journal`** that contain **`ERROR`**, and only those, one per line.

### Task 7 (5%): context `cka-appli`

Update the Deployment **`vitrine`** to the **nginx 1.30.6** image, then bring it
back to the previous version with a **rollback**.

### Task 8 (5%): context `cka-appli`

Create the ConfigMap **`reglages`** (key `mode`, value `production`) and the
Secret **`acces`** (key `mot-de-passe`, value `jeton-de-demonstration`). The
container of the Deployment **`api`** must receive the variable **`MODE`** from
the ConfigMap, and the variable **`MOT_DE_PASSE`** from the Secret.

### Task 9 (5%): context `cka-appli`

The node `k8s-w1.lab` carries the taint `examen=reserve:NoSchedule` and the
label `role-examen=rapports`. Run **all** the Pods of the Deployment
**`rapport`** on that node, and only there, **without removing the taint** and
without naming the node. This task requires task 3 done.

### Task 10 (10%): context `cka-appli`

Create the ServiceAccount **`lecteur`**, and give it the right to **get, list
and watch the Pods** of the `appli` namespace, and **nothing else**.

### Task 11 (5%): context `cka-infra`

Save an etcd snapshot into **`/var/lib/etcd/sauvegarde-examen.db`** on
`k8s-cp.lab`. etcd runs in the Pod `etcd-k8s-cp.lab` of the `kube-system`
namespace, with its certificates under `/etc/kubernetes/pki/etcd/`.

### Task 12 (5%): context `cka-appli`

Install the definition **`~/examen/crd-sauvegarde.yaml`**, then create in
`appli` the **`Sauvegarde`** resource named **`quotidienne`**, with source
**`base`** and a retention of **`7`** days.

### Task 13 (5%): context `cka-infra`

Complete the overlay **`~/examen/kustomize/overlays/prod/`** so that it places
the application in the **`prod`** namespace, with **3 replicas** and the label
**`env: prod`** on the Deployment and its Pods, then apply it.

### Task 14 (5%): context `cka-reseau`

Only the Pod **`front`** may reach the database **`db`** on port **5432**. The
Pod `autre`, in the same namespace, is refused.

### Task 15 (5%): context `cka-reseau`

Create the Ingress **`boutique`**, of class `traefik`, which sends
`http://boutique.examen/api` to the Service **`api`**. The controller answers on
the node's port **30080**.

### Task 16 (5%): context `cka-reseau`

With the Gateway API, serve the host **`magasin.examen`** through the Service
**`web`**: a Gateway of class `traefik`, on port 80, and an HTTPRoute named
**`magasin`**, accepted by that Gateway.

### Task 17 (5%): context `cka-reseau`

Publish the Deployment **`accueil`** (it listens on port 5678) through a Service
**`accueil`** of type **NodePort**, on port **30092** of every node.

## How you will be graded

Twenty states, 5 points each; the 10% tasks carry two. The weights follow those
of the domains of the official CKA curriculum. The threshold is **66 out of
100**, as in the real exam: 14 states out of 20 are needed. No hint is offered,
and the feedback is the verdict only, as on exam night.

## What this mock exam does not reproduce

- **One cluster per task**: the real exam chains several. Here, the three
  contexts point at the same cluster, with different namespaces.
- **The remote desktop and its browser** limited to the official documentation.
- **The timer**, which you keep yourself.
- **Partial credit** inside a state: a state is passed or not.

```bash
dsoxlab check  cka-examen-blanc
dsoxlab submit cka-examen-blanc
```
