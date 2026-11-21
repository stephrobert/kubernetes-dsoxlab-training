# Bring down a CIS audit count, and check it with a second audit

The lesson presents the CIS Benchmark and the kube-bench tool that checks it.
Here, auditing and fixing the control plane is the challenge: this course
audits a **worker**. It adds cases the lesson does not show: kube-bench run as
a Job on a given node, the `node` target, reading the summary, the list of
gaps, then one check read with its remediation.

You work in a scratch namespace, `essai-cis`, with a Job of your own,
`essai-bench-noeud`. The challenge has its own Job: you will do it on your
own, at the end.

Related page: [CIS Kubernetes Benchmark: audit your cluster security](https://www.stephane-robert.info/en/docs/devsecops/runtime/cis-benchmark/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-cis-benchmark-remediate
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and kube-bench v0.16.0.

Run kube-bench as a Job on the `k8s-w1.lab` worker, with the `node` target.
kube-bench reads the node's files: the Job mounts them read-only and shares
the node's process space (`hostPID`) to see the kubelet.

```bash
kubectl create namespace essai-cis; cat <<YAML | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: essai-bench-noeud
  namespace: essai-cis
spec:
  backoffLimit: 0
  template:
    spec:
      nodeName: k8s-w1.lab
      hostPID: true
      restartPolicy: Never
      containers:
        - name: kube-bench
          image: aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679
          command: [kube-bench, run, --targets, node]
          volumeMounts:
            - {name: var-lib-kubelet, mountPath: /var/lib/kubelet, readOnly: true}
            - {name: etc-systemd, mountPath: /etc/systemd, readOnly: true}
            - {name: lib-systemd, mountPath: /lib/systemd, readOnly: true}
            - {name: etc-kubernetes, mountPath: /etc/kubernetes, readOnly: true}
            - {name: usr-bin, mountPath: /usr/local/mount-from-host/bin, readOnly: true}
      volumes:
        - {name: var-lib-kubelet, hostPath: {path: /var/lib/kubelet}}
        - {name: etc-systemd, hostPath: {path: /etc/systemd}}
        - {name: lib-systemd, hostPath: {path: /lib/systemd}}
        - {name: etc-kubernetes, hostPath: {path: /etc/kubernetes}}
        - {name: usr-bin, hostPath: {path: /usr/bin}}
YAML
kubectl wait --for=condition=Complete job/essai-bench-noeud -n essai-cis --timeout=180s
```

```text
namespace/essai-cis created
job.batch/essai-bench-noeud created
job.batch/essai-bench-noeud condition met
```

## 📊 Exercise 1: the summary

The report is in the logs of the Job's Pod. Read the summary:

```bash
kubectl logs job/essai-bench-noeud -n essai-cis | grep -A4 '^== Summary node'
```

```text
== Summary node ==
17 checks PASS
2 checks FAIL
6 checks WARN
0 checks INFO
```

17 checks passed, 2 failed, 6 warnings. A `WARN` is a **manual** check:
kube-bench cannot decide on its own, it is up to you to check.

## 📋 Exercise 2: the gaps

List the checks that failed or gave a warning:

```bash
kubectl logs job/essai-bench-noeud -n essai-cis | grep -E '^\[(FAIL|WARN)\]'
```

```text
[FAIL] 4.1.1 Ensure that the kubelet service file permissions are set to 600 or more restrictive (Automated)
[WARN] 4.1.3 If proxy kubeconfig file exists ensure permissions are set to 600 or more restrictive (Manual)
[WARN] 4.1.4 If proxy kubeconfig file exists ensure ownership is set to root:root (Manual)
[FAIL] 4.1.9 If the kubelet config.yaml configuration file is being used validate permissions set to 600 or more restrictive (Automated)
[WARN] 4.2.9 Ensure that the --tls-cert-file and --tls-private-key-file arguments are set as appropriate (Manual)
[WARN] 4.2.12 Ensure that the Kubelet only makes use of Strong Cryptographic Ciphers (Manual)
[WARN] 4.2.13 Ensure that a limit is set on pod PIDs (Manual)
[WARN] 4.2.14 Ensure that the --seccomp-default parameter is set to true (Manual)
```

Both failures are about **file permissions**: the kubelet's service file and
its configuration file are too open. `(Automated)` means kube-bench checked it
itself, `(Manual)` that it could not.

## 🔧 Exercise 3: a check and its remediation

At the end of the report, each gap has its remediation. Read the first one
(`contrôle` means "check"):

```bash
N=$(kubectl logs job/essai-bench-noeud -n essai-cis | grep -m1 -E '^\[(FAIL|WARN)\]' | awk '{print $2}'); echo "contrôle $N"; kubectl logs job/essai-bench-noeud -n essai-cis | sed -n '/^== Remediations node/,/^== Summary/p' | grep -A2 "^$N "
```

```text
contrôle 4.1.1
4.1.1 Run the below command (based on the file location on your system) on the each worker node.
For example, chmod 600 /lib/systemd/system/kubelet.service
```

The remediation gives the command, with the file's path on this system. It is
run on the audited node, here `k8s-w1.lab`. A fix only counts once checked by
a second audit.

## 🧹 Clean-up

Delete the scratch namespace, and the Job with it:

```bash
kubectl delete namespace essai-cis
```

```text
namespace "essai-cis" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-cis-benchmark-remediate
dsoxlab check cks-cis-benchmark-remediate
```

```text
╭─ Result: cks-cis-benchmark-remediate ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests      │
╰───────────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: audit the control plane, make three checks
that share the same flaw pass, and prove it with a second audit.

```bash
dsoxlab run cks-cis-benchmark-remediate
dsoxlab challenge cks-cis-benchmark-remediate
```
