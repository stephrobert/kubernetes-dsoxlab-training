# Rebuild an incident from the Events of a namespace

**CKA** lab, *Troubleshooting* domain, competencies "Troubleshoot clusters and
nodes" and "Troubleshoot components".

Events are the immediate alert log of the cluster. This lab has you read those
of a namespace where four applications went down, each in a different way, to
name each fault and find which one started.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 20 minutes |
| Lesson | [Analyser les événements Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/analyser-evenements-kubernetes/) (French) |

```bash
dsoxlab run   k8s-reconstituer-un-incident-par-les-evenements
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```
