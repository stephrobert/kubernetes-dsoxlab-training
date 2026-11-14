# Fix a cluster's CIS findings, without guidance

## The situation

The kubeadm cluster comes out of a default install. The compliance team ran a
CIS audit on it and wants two things before the next review: the findings
that can be fixed without changing the architecture are fixed, and the
cluster keeps a trace of **who reads its Secrets**.

Today the API server exposes its Go profiler, nothing is audited, and the
control plane carries the settings kubeadm writes by default.

The audit tool is ready: the **kube-bench** Job is written on the node, at
`/root/kube-bench-job.yaml`, and runs in the **`conformite`** namespace. That
namespace also holds the **`jeton-de-paiement`** Secret, the one the
compliance team wants to see traced. Setup has already run the audit once and
kept its failure count.

You are on the control plane, with `kubectl` and `sudo`. No procedure is
given: the module taught you what you need.

## What you must achieve

1. The **API server** runs with its profiler **off**, checks that a presented
   service account token **still exists**, and refuses TLS versions below a
   **floor** you set.
2. The profiler at `/debug/pprof/` **no longer answers**, and the API server
   **still answers** ordinary requests.
3. The finding the CIS audit holds against the **API server**, the
   **controller manager** and the **scheduler**, checks **1.2.15**, **1.3.2**
   and **1.4.1**, is fixed on **all three**.
4. kube-bench, **run again**, passes those three checks and counts **fewer
   failures** than at the start.
5. An **audit policy** at `/etc/kubernetes/audit-policy.yaml` records accesses
   to **Secrets in full**, request and response, and **everything else as
   metadata** only.
6. The API server **runs with that audit**: it reads that policy and writes its
   log to `/var/log/kubernetes/audit.log` on the node, and it still answers.
7. The log **actually** holds the trace of a Secret read, in full, and that of
   an ordinary read, as metadata only.

## How you will be graded

Seven states, equally weighted. The pass mark is **70 out of 100**, and states
**4 and 7** are **blocking**: the audit run again, and the log that traces.
Passing the others does not make up for missing one of them.

The tests read the manifests on the node, run kube-bench themselves and
compare its count with the one setup measured, then make two real reads and
read back what the API server has just written. The feedback is limited to
the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-durcir-le-plan-de-controle
dsoxlab submit k8s-challenge-durcir-le-plan-de-controle
```
