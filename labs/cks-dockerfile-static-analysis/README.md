# Analyse a Dockerfile before building the image

The lesson shows how `trivy config` reads a Dockerfile and says, finding by
finding, what to fix. This course adds what you need to use it day to day:
analyse a Kubernetes manifest with the same tool, keep only the serious
findings, make a CI pipeline fail through the exit code, and set a finding
aside in a visible way.

You work in the `~/essai-recette` folder, with a Python recipe and a Pod
manifest. The challenge targets another Dockerfile: you will do it on your
own, at the end.

Related page: [Secure the supply chain](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-dockerfile-static-analysis
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). `trivy` is installed on it.

The outputs shown in this course were recorded on this machine on
22 November 2026, with trivy 0.74.0.

Write a Python recipe and a privileged Pod manifest in a test folder:

```bash
mkdir -p ~/essai-recette; cat > ~/essai-recette/Dockerfile <<'DF'
FROM python:3.13
RUN pip install flask
COPY app.py /app.py
CMD python /app.py
DF
cat > ~/essai-recette/pod.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: recette
spec:
  containers:
    - name: app
      image: python:3.13
      securityContext:
        privileged: true
YAML
trivy --version | head -1
```

```text
Version: 0.74.0
```

## 📄 Exercise 1: the same analysis, on a Kubernetes manifest

`trivy config` does not only read Dockerfiles: it also recognises Kubernetes
manifests, and analyses them with its own rules. Run it on the folder:

```bash
trivy config --quiet ~/essai-recette 2>/dev/null | grep -E '^(Dockerfile|pod.yaml)|Failures|^[A-Z]+:|KSV-|DS-' | head -14
```

```text
Dockerfile (dockerfile)
Failures: 2 (UNKNOWN: 0, LOW: 1, MEDIUM: 0, HIGH: 1, CRITICAL: 0)
DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
DS-0026 (LOW): Add HEALTHCHECK instruction in your Dockerfile
pod.yaml (kubernetes)
Failures: 17 (UNKNOWN: 0, LOW: 11, MEDIUM: 3, HIGH: 3, CRITICAL: 0)
KSV-0001 (MEDIUM): Container 'app' of Pod 'recette' should set 'securityContext.allowPrivilegeEscalation' to false
KSV-0003 (LOW): Container 'app' of Pod 'recette' should add 'ALL' to 'securityContext.capabilities.drop'
KSV-0004 (LOW): Container 'app' of 'pod' 'recette' in 'default' namespace should set securityContext.capabilities.drop
KSV-0011 (LOW): Container 'app' of Pod 'recette' should set 'resources.limits.cpu'
KSV-0012 (MEDIUM): Container 'app' of Pod 'recette' should set 'securityContext.runAsNonRoot' to true
KSV-0014 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.readOnlyRootFilesystem' to true
KSV-0015 (LOW): Container 'app' of Pod 'recette' should set 'resources.requests.cpu'
KSV-0016 (LOW): Container 'app' of Pod 'recette' should set 'resources.requests.memory'
```

Two files, two families of findings. Those of the Dockerfile start with
`DS-`, those of the manifest with `KSV-`. The Pod piles up 17: no non-root
user, no resource limits, privileged container… A single tool thus covers the
recipe of the image and the way it will be started.

## 🎯 Exercise 2: keep only the serious ones

17 findings at once drown what matters. `--severity` filters by severity:

```bash
trivy config --quiet --severity HIGH,CRITICAL ~/essai-recette 2>/dev/null | grep -E 'Failures|KSV-|DS-' | head -8
```

```text
Failures: 1 (HIGH: 1, CRITICAL: 0)
DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
Failures: 3 (HIGH: 3, CRITICAL: 0)
KSV-0014 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.readOnlyRootFilesystem' to true
KSV-0017 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.privileged' to false
KSV-0118 (HIGH): pod recette in default namespace is using the default security context, which allows root privileges
```

One high finding is left on the Dockerfile (no non-root `USER`) and three on
the manifest, including the privileged container. That is where to start.

## 🚦 Exercise 3: make a CI pipeline fail

By default, `trivy config` exits with 0 even when it finds something: it
informs, it blocks nothing. `--exit-code 1` makes it exit with 1 as soon as a
finding of the requested level remains. Compare two thresholds:

```bash
trivy config --quiet --severity CRITICAL --exit-code 1 ~/essai-recette >/dev/null 2>&1; echo "critiques : code $?"; trivy config --quiet --severity HIGH --exit-code 1 ~/essai-recette >/dev/null 2>&1; echo "élevés : code $?"
```

```text
critiques : code 0
élevés : code 1
```

No critical finding, so code 0. At least one high finding, so code 1: a CI
pipeline that runs this command stops there. Each team picks its threshold,
and raises it as the fixes come in.

## 🙈 Exercise 4: set a finding aside, and say so

A finding you accept goes into a `.trivyignore` file, one ID per line, rather
than lowering the threshold for everyone. Set aside the first finding found,
then run the analysis again from the folder:

```bash
ID=$(trivy config --quiet -f json ~/essai-recette 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sorted({m["ID"] for r in d.get("Results",[]) for m in r.get("Misconfigurations") or []})[0])'); echo "constat ignoré : $ID"; echo "$ID" > ~/essai-recette/.trivyignore; cd ~/essai-recette && trivy config --quiet . 2>/dev/null | grep -c "$ID"; echo "(occurrences restantes de $ID)"
```

```text
constat ignoré : DS-0002
0
(occurrences restantes de DS-0002)
```

`DS-0002` no longer shows up. Watch out: trivy reads `.trivyignore` from the
**current directory**, not from the analysed folder, hence the `cd`. The file
stays in the repository, next to the Dockerfile: anyone who reads it sees what
was set aside. Setting a finding aside is not fixing it, and it is not what
the challenge asks.

## 🧹 Clean-up

Delete the test folder:

```bash
rm -rf ~/essai-recette
```

```text

```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-dockerfile-static-analysis
dsoxlab check cks-dockerfile-static-analysis
```

```text
╭─ Result: cks-dockerfile-static-analysis ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests         │
╰──────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Node Dockerfile the analysis holds five
findings against, to fix them all without changing what the image does.

```bash
dsoxlab run cks-dockerfile-static-analysis
dsoxlab challenge cks-dockerfile-static-analysis
```
