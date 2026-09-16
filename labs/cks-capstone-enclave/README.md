# Capstone: open an enclave for a team you do not trust

**CKS** capstone. It crosses three of the exam's six domains: *Minimize
Microservice Vulnerabilities* (20 %), *Cluster Hardening* (15 %) and *Cluster
Setup* (15 %), that is **50 %** of the blueprint.

**None of the five requirements names a Kubernetes object.** That is what sets
a capstone apart from a micro-lab: a lab called `networkpolicy-default-deny`
has already answered half the question before the candidate opens a terminal.
Here, one must decide **what to put in place**.

Pass mark: **66 %**, four requirements out of five.

## Two active proofs, and why they are needed

Two of the five tests do not re-read what the candidate put in place, they
**attempt what must be refused**:

- the admission test really creates a privileged Pod in the enclave and
  requires the cluster to reject it. A mistyped admission label is accepted
  without complaint by the API, refuses nothing, and yet reads like the
  others;
- the network test queries the service from both witnesses. A NetworkPolicy
  whose selector designates nobody is a perfectly valid object that protects
  nothing.

The network test also carries the capstone's costliest trap: "the intruder
does not reach the vault" would be green **before the work**, for the worst of
reasons, the vault not existing yet. Requiring first that the declared caller
gets through is what rules out that false green.

## A setup detail that is not one

The `autorise` witness Pod is placed **inside** the enclave, before the
candidate imposes anything there. Admission only judges at **creation time**: a
Pod already there survives the rule set afterwards. It is nonetheless written
compliant with the `restricted` level, so that a candidate who deleted it
could recreate it identically.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 45 minutes |
| Companion lesson | [Pod Security Standards](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |

```bash
dsoxlab run   cks-capstone-enclave
dsoxlab check cks-capstone-enclave
```

The `cleanup.yaml` also takes back **cluster-scoped** objects a candidate
might have created: a ClusterRole left behind would skew the next lab, and the
validator's snapshot sees it.
