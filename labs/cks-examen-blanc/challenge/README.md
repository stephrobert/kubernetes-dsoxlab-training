# Challenge: CKS mock exam: 16 tasks in 120 minutes

## Before you start

This exam follows the CKS format: hands-on tasks, graded on the final state of
the cluster, with no hint. **Plan for 120 minutes**, in one sitting, and start
your own timer: the tool does not. The tasks are independent of each other.

You start from the **base**, `k8s-cp.lab`, the session `dsoxlab run` opens.
**Each task names the host to do it on**: connect with `ssh`, work, then go
back to the base with `exit` before the next task. Never run `ssh` from a task
host. Both hosts, **`k8s-cp.lab`** and **`k8s-w1.lab`**, have `kubectl`
configured, the `k` alias and completion, and your account uses `sudo` without
a password. **No context sets the namespace**: each task gives its own, write
it in your commands. A resource created in the wrong namespace does not count.

The image to use when a task asks you to create a Pod:

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The tasks

### Task 1 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`zone`**

The Pods `db`, `annuaire`, `web` and `intrus` reach each other freely. Deny
**all incoming and outgoing traffic by default** for every Pod of the
namespace, then allow only: **`web` to `db` on TCP port 80**, and **name
resolution** for the Pods of the namespace (the cluster DNS, port 53 in UDP and
TCP). Nothing else.

Then go back to the base: `exit`.

### Task 2 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`vitrine`**

The Ingress **`site`** publishes `vitrine.lab`. The controller already answers
in HTTPS on the node's port **30443**, but with its own default certificate.
Create a **self-signed certificate whose subjectAltName names `vitrine.lab`**,
store it in the TLS Secret **`vitrine-tls`**, and make the Ingress `site` serve
`vitrine.lab` in HTTPS with it. A client that trusts this certificate must get
the site.

Then go back to the base: `exit`.

### Task 3 (5%)

**Connect: `ssh k8s-cp.lab`** · no namespace (control plane)

The CIS audit of the control plane with kube-bench reports the **profiling**
checks of the **API server**, the **controller manager** and the
**scheduler** as `FAIL`. The audit Job is ready in
**`~/examen/kube-bench-job.yaml`** (namespace `conformite`; delete a finished
Job before running it again). Fix the three components so that a new audit
reports these checks as `PASS`, without breaking the control plane.

Then go back to the base: `exit`.

### Task 4 (10%)

**Connect: `ssh k8s-w1.lab`** · namespace **`equipe-dev`**

The ServiceAccount **`dev-sa`** is bound to `cluster-admin` by the
ClusterRoleBinding **`dev-admin-binding`**. Take that power back. `dev-sa`
keeps **get, list, watch, create, update, patch and delete** on the **Pods,
Services and Deployments** of `equipe-dev`, through a Role and a RoleBinding of
that namespace, and **nothing else**: no Secret, and nothing outside
`equipe-dev`.

Then go back to the base: `exit`.

### Task 5 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`releves`**

The Deployment **`releveur`** runs with the namespace's `default`
ServiceAccount, and its Pods carry an API token they never use. Create the
ServiceAccount **`releveur`**, which **never mounts its token automatically**,
and make the Deployment use it. The `default` ServiceAccount of `releves` must
not mount its token automatically either.

Then go back to the base: `exit`.

### Task 6 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`confinement`**

On `k8s-w1.lab`, the AppArmor profile file
**`/etc/apparmor.d/k8s-refuser-ecriture`** exists but is not loaded. Load it in
**enforce** mode. Then create the Pod **`confine`** (busybox image, command
`sleep infinity`) on `k8s-w1.lab`, confined by that profile, **declared in its
`securityContext`**.

Then go back to the base: `exit`.

### Task 7 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`confinement`**

On `k8s-cp.lab`, create the seccomp profile **`restrict-chmod.json`** in the
kubelet's local profiles directory, under `profiles/` in
`/var/lib/kubelet/seccomp/`. It **allows every call by default** and
**refuses `chmod`, `fchmod` and `fchmodat`**. Then create the Pod
**`seccomp-pod`** (busybox image, command `sleep infinity`) on `k8s-cp.lab`,
with that profile. The Pod `temoin` must keep its right to call `chmod`.

Then go back to the base: `exit`.

### Task 8 (10%)

**Connect: `ssh k8s-w1.lab`** · namespace **`durci`**

The namespace accepts anything: the Pod `laxiste` shares the host's PID
namespace and runs as root. Apply the **`restricted`** Pod Security Standard to
`durci` in **all three modes** (enforce, warn and audit). Then create there the
Pod **`conforme`** (busybox image, command `sleep infinity`) that satisfies
this standard. Leave `laxiste` alone.

Then go back to the base: `exit`.

### Task 9 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`production`**

The Pod **`insecure-app`** was created in a hurry. Create the Pod
**`secure-app`** doing the same work (busybox, command `sh -c "sleep 86400"`),
with **none of its flaws**: no host namespace, not privileged, no privilege
escalation, a non-root user, every capability dropped, and an image pinned to a
version. Then **delete `insecure-app`**.

Then go back to the base: `exit`.

### Task 10 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`tresor`**

The Deployment **`facturation`** receives its API key as the literal
environment variable `CLE_API`. Store that value in the Secret **`cle-api`**,
key **`cle`**. The container must read it as the **read-only file
`/etc/tresor/cle`**, and **no environment variable** may carry it any more.

Then go back to the base: `exit`.

### Task 11 (10%)

**Connect: `ssh k8s-cp.lab`** · namespace **`chaine`**

The Deployment **`pinned-app`** names its image by the tag `nginx:1.30.5`.
Reference **that same image by its digest only** (`nginx@sha256:...`), the one
the node runs, without changing version. Then make the cluster **refuse**, in
the namespace `chaine` **and only there**, the creation of any Pod whose image
is not pinned by digest, with a **ValidatingAdmissionPolicy** and its binding.

Then go back to the base: `exit`.

### Task 12 (5%)

**Connect: `ssh k8s-cp.lab`** · no namespace (file on the node)

`trivy config` reports five findings against
**`~/examen/inventaire/Dockerfile`**: `DS-0001`, `DS-0002`, `DS-0004`,
`DS-0026` and `DS-0029`. Fix the file so that **these five findings
disappear**. It must still start from a Node image and run `server.js`. trivy
is installed on `k8s-cp.lab`.

Then go back to the base: `exit`.

### Task 13 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`chaine-signature`**

A local registry answers on `localhost:5000` of `k8s-cp.lab`. It holds
`localhost:5000/appli/web:1.0` and `localhost:5000/appli/outil:1.0`, and
neither is signed. `cosign` and `crane` are installed. Generate a key pair in
**`/root`** (an empty password is accepted), **sign `appli/web:1.0`** with it,
and publish the **public key** in the ConfigMap **`cosign-pub-key`**, under the
key **`cosign.pub`**. The private key does not leave the node.

Then go back to the base: `exit`.

### Task 14 (10%)

**Connect: `ssh k8s-cp.lab`** · namespace **`coffre`**

Make the API server **record accesses to Secrets with the full body** of the
request and the response, and **everything else at `Metadata` level only**.
The policy goes in **`/etc/kubernetes/audit-policy.yaml`**, the log in
**`/var/log/kubernetes/audit.log`**. The Secret `dossier-medical` of `coffre` is
there to be read. The API server must still answer afterwards.

Then go back to the base: `exit`.

### Task 15 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`catalogue`**

The Deployment **`vitrine`** runs as an unprivileged user, yet its container
can still write to its own filesystem, its configuration included. Make that
**filesystem read-only**, forbid **privilege escalation**, drop **every
capability**, and declare that the process **does not run as root**. The site
must keep answering on `http://vitrine.catalogue.svc.cluster.local/` from the
Pod `client`. Modify the Deployment, do not replace it.

Then go back to the base: `exit`.

### Task 16 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`atelier`**

On `k8s-w1.lab`, **one** of the four Pods `atelier-1` to `atelier-4` runs a
cryptominer named **`kdevtmpfsi`**, started after the Pod itself: their specs
are identical. Find which one, and **delete that Pod only**.

Then go back to the base: `exit`.

## How you will be graded

Twenty requirements, 5 points each; the 10% tasks carry two. The weights follow those
of the six domains of the official CKS curriculum. The threshold is **67 out of
100**, as in the real exam: 14 requirements out of 20 are needed. No hint is offered,
and the feedback is the verdict only, as on exam night.

## What this mock exam does not reproduce

- **One cluster per task**: the real exam chains several. Here, both hosts
  point at the same cluster, with different namespaces.
- **The remote desktop and its browser** limited to the official documentation.
- **The timer**, which you keep yourself.
- **Partial credit** inside a state: a state is passed or not.

```bash
dsoxlab check  cks-examen-blanc
dsoxlab submit cks-examen-blanc
```
