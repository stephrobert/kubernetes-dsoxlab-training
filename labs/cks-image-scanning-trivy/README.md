# Scan an image and pick a less vulnerable version

The lesson shows how to scan an image with Grype and Trivy, and how to read a
vulnerability (CVE) report. This course adds four moves it does not show:
setting a vulnerability aside until a date, separating the vulnerabilities of
the system from those of the application, scanning the exact image a node
runs, and scanning an inventory (SBOM) again without pulling the image.

You work in the `~/essai-trivy` folder, with the `redis` and `python` images.
The challenge targets another image: you will do it on your own, at the end.

Related page: [Scan images](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-image-scanning-trivy
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). `trivy` is installed on it.

The outputs shown in this course were recorded on this machine on
22 November 2026, with trivy 0.74.0. Vulnerability counts change every day, as
CVEs get published: yours will be different.

Create the test folder:

```bash
mkdir -p ~/essai-trivy && trivy --version | head -1
```

```text
Version: 0.74.0
```

The commands of this course use an **output template** (`--format
template`): for each part of the analysed image, it prints its type and its
number of vulnerabilities. An image often holds several: the system packages
(`debian`), a Go binary (`gobinary`), Python libraries (`python-pkg`)…

## 📅 Exercise 1: set a vulnerability aside until a date

Count the high and critical vulnerabilities of the `redis` image:

```bash
cd ~/essai-trivy && trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
debian : 59
gobinary : 60
```

Two parts: the Debian system, and `gosu`, a Go binary shipped in the image.
Now set the first high vulnerability aside until 31 December 2026, with `exp:`
in the `.trivyignore` file:

```bash
cd ~/essai-trivy && ID=$(trivy image --quiet --scanners vuln --severity HIGH --format json redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1 | grep -o '"VulnerabilityID": "[^"]*"' | head -1 | cut -d'"' -f4); echo "$ID exp:2026-12-31" > .trivyignore; cat .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
CVE-2026-109518 exp:2026-12-31
debian : 57
gobinary : 60
```

The Debian part goes from 59 to 57: the same vulnerability affected two
packages. Change the date to a past one:

```bash
cd ~/essai-trivy && sed -i 's/exp:2026-12-31/exp:2026-01-01/' .trivyignore; cat .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
CVE-2026-109518 exp:2026-01-01
debian : 59
gobinary : 60
```

The vulnerability comes back on its own: a dated exception expires, and nobody
has to remember to remove it. An exception without a date stays forever.

## 🧩 Exercise 2: the system on one side, the application on the other

`--pkg-types` limits the scan to one family of packages. First count the
vulnerabilities of the system of the `python` image:

```bash
cd ~/essai-trivy && rm -f .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL --pkg-types os python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0
```

```text
debian : 78
```

Then those of the Python libraries it holds:

```bash
cd ~/essai-trivy && trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL --pkg-types library python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0
```

```text
python-pkg : 0
```

78 vulnerabilities in the system, none in the libraries. This split tells who
fixes what: the system ones go away by changing the base image, the library
ones by changing the dependencies of the application. Those are not the same
teams.

## 🖥️ Exercise 3: scan what the node actually has

A scan by image name pulls the image from the registry, which may have changed
since. To scan the exact image a node runs, read it from containerd. Several
versions may sit side by side:

```bash
sudo crictl images | grep -E 'IMAGE|kube-proxy'
```

```text
IMAGE                                      TAG                 IMAGE ID            SIZE
registry.k8s.io/kube-proxy                 v1.36.6             c407131a44390       30.1MB
registry.k8s.io/kube-proxy                 v1.37.2             55b428162aa8c       30.2MB
```

Two versions of kube-proxy: the old one stays after an upgrade. Take the one
the kube-proxy Pod of the node really uses, and scan it in containerd:

```bash
IMG=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-cp.lab -o jsonpath='{.items[0].spec.containers[0].image}'); echo "image du Pod kube-proxy : $IMG"; sudo CONTAINERD_NAMESPACE=k8s.io trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --image-src containerd --severity HIGH,CRITICAL $IMG
```

```text
image du Pod kube-proxy : registry.k8s.io/kube-proxy:v1.37.2
debian : 1
gobinary : 0
gobinary : 0
gobinary : 6
```

Two settings matter here: `--image-src containerd`, to read the image on the
node, and `CONTAINERD_NAMESPACE=k8s.io`, because Kubernetes stores its images
in the `k8s.io` namespace of containerd, not in `default` where trivy looks
otherwise. kube-proxy holds several Go binaries, hence several `gobinary`
lines.

## 📦 Exercise 4: scan an SBOM instead of the image

An SBOM is the inventory of everything an image holds. Generate the one of the
`redis` image, in CycloneDX format:

```bash
cd ~/essai-trivy && trivy image --quiet --format cyclonedx --output redis.cdx.json redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1; ls -l redis.cdx.json | awk '{print $5, $9}'
```

```text
199629 redis.cdx.json
```

Now scan that file, without the image:

```bash
cd ~/essai-trivy && trivy sbom --quiet --severity HIGH,CRITICAL --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' redis.cdx.json
```

```text
debian : 59
gobinary : 60
```

The numbers are those of the image scan. The SBOM, archived at each delivery,
can be scanned again when new CVEs are published, without pulling or
rebuilding the image.

## 🧹 Clean-up

Delete the test folder:

```bash
rm -rf ~/essai-trivy; ls -d ~/essai-trivy
```

```text
ls: cannot access '/home/ansible/essai-trivy': No such file or directory
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-image-scanning-trivy
dsoxlab check cks-image-scanning-trivy
```

```text
╭─ Result: cks-image-scanning-trivy ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests   │
╰────────────────────────────────────╯
```

That is the expected result on a fresh lab. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application in production on a
vulnerable version, to move to a version that carries fewer critical
vulnerabilities, with a scan to back the choice.

```bash
dsoxlab run cks-image-scanning-trivy
dsoxlab challenge cks-image-scanning-trivy
```
