# Override the values of a Helm chart without falling into the typing trap

**CKAD** lab, *Application Deployment* domain, competency "Use the Helm
package manager to deploy existing packages".

A chart upgrade silently loses settings set by hand, and `--set` changes the
type of a value that looks like a number. This lab has you upgrade a release
while keeping the operations settings and setting a value that must stay a
string, with Helm 4.3.2.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 20 minutes |
| Lesson | [Les values Helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/values/) (French) |

```bash
dsoxlab run   k8s-surcharger-les-values-d-un-chart-helm
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```
