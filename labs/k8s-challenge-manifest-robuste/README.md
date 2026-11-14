# Ship a robust manifest from a set of requirements

Challenge of the **Deploy your applications** module of the Kubernetes course, in
the Mettre en pratique section of the "Debug an application" lesson: an
application shipped by Kustomize in two variants, with init container, native
sidecar, budgets and probes, a CronJob, a Job, and a failing Pod to diagnose
before repairing it. Ten requirements, pass mark 70, three blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up the `expedition` namespace and a failing Pod |
| Duration | about 60 minutes |
| Related page | [Débugger une application, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |

```bash
dsoxlab run    k8s-challenge-manifest-robuste
dsoxlab check  k8s-challenge-manifest-robuste
dsoxlab submit k8s-challenge-manifest-robuste
```
