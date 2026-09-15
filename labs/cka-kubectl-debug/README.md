# Get inside a container with no shell using kubectl debug

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competencies
"Troubleshoot clusters and nodes" and "Manage and evaluate container output
streams".

Distroless images have neither a shell nor tools, and `kubectl exec` fails on
them. The exam expects you to know how to get in anyway, and how to reach a
node without an SSH session.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Debugging an application](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |

```bash
dsoxlab run   cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```

Ported from K8sExamLab on 2026-09-14, then played through: 0 before the work,
100 after the trainer's solution.
