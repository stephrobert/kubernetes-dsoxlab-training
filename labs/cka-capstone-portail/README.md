# Capstone: bring the portal back, with nobody left to ask

The catalogue's first **CKA capstone**. It does not target one blueprint
competency, it crosses four: *Troubleshooting* (30 %), *Services and
Networking* (20 %), *Workloads and Scheduling* (15 %) and *Storage* (10 %),
which is 75 % of the exam.

A micro-lab announces its subject in its title. `cka-troubleshoot-dns` teaches
how to repair DNS, and says up front that DNS is the problem: half the
question is answered before the candidate opens a terminal. Here the
`production` namespace holds **three independent faults** and nothing says
which. Fixing the first one you find makes nothing answer.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 45 minutes |
| Pass mark | 66 %, the CKA exam threshold |
| Companion lesson | [CKA exercises](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

```bash
dsoxlab run    cka-capstone-portail
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```

Eight tests, measuring effects rather than manifests: the faulty selector can
be fixed on the Service or on the Pods, and the storage by creating a volume
or by rewriting the claim. The last one queries the portal from **each** of
the two nodes, the way monitoring will.

Written on 2026-09-15, then validated by `scripts/valider-labs.py`: 0 before
the work, 100 after the trainer's solution, replayable and leaving no trace.
