# Capstone: ship the shop, from the specification alone

The catalogue's first **CKAD capstone**. It does not target one blueprint
competency, it crosses five: *Application Design and Build*, *Application
Deployment*, *Application Environment, Configuration and Security*,
*Application Observability* and *Services and Networking*.

A micro-lab announces its subject in its title. `cka-troubleshoot-dns` teaches
how to repair DNS, and says up front that DNS is the problem: a learner can
get very good at that exercise without ever having had to work out where to
look. This capstone names no Kubernetes object. It gives six requirements and
an empty namespace, and leaves the candidate to pick the tools, as the exam
does.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 45 minutes |
| Pass mark | 66 %, the CKAD exam threshold |
| Companion lesson | [Deployments](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

```bash
dsoxlab run    ckad-capstone-boutique
dsoxlab check  ckad-capstone-boutique
dsoxlab submit ckad-capstone-boutique
```

Ten tests, half of which step inside the container: a conforming manifest that
does not produce the expected effect earns nothing. The last one proves the
isolation in both directions, `frontend` getting through and `intrus` being
blocked.

Written on 2026-09-15, then validated by `scripts/valider-labs.py`: 0 before
the work, 100 after the trainer's solution, replayable and leaving no trace.
