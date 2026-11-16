# Inspect a failed Helm release and restore it

**CKAD** lab, *Application Deployment* domain, competency "Use the Helm
package manager to deploy existing packages".

A failed upgrade leaves a release in a state you must read first, then repair.
This lab has you search for a chart, read the history of a release, go back to
the last healthy revision and run the chart's tests, with Helm 4.3.2.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 20 minutes |
| Lesson | [La commande helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/commande-helm/) (French) |

```bash
dsoxlab run   k8s-inspecter-et-restaurer-une-release-helm
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
