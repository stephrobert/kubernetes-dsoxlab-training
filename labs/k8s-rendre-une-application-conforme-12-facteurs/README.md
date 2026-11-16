# Make an application 12-factor compliant on Kubernetes

**CKAD** lab, *Application Design and Build* domain.

An application deployed on Kubernetes is not 12-factor compliant for all
that: the cluster applies what you declare, it checks no factor. This lab has
you take over a faulty application, factor by factor: configuration, state,
clean shutdown and administration task.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 30 minutes |
| Lesson | [Rendre une application conforme au 12-factor sur Kubernetes](https://www.stephane-robert.info/docs/conteneurs/cloud-native/application-12-factor-kubernetes/) (French) |

```bash
dsoxlab run   k8s-rendre-une-application-conforme-12-facteurs
dsoxlab check k8s-rendre-une-application-conforme-12-facteurs
```
