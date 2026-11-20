# Compose a multi-container Pod: init container, native sidecar, shared volumes

Challenge of the Kubernetes training, in the Put it into practice section of
the "Init containers and sidecars" lesson: a Deployment whose Pods prepare
their page with an init container, serve it read-only, and pass on their
access log through a native sidecar from a bounded shared volume. Five
requirements, pass mark 80%, two of them blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the lab sets up the `photo` namespace |
| Duration | about 40 minutes |
| Related pages | [Init containers and sidecars](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/init-containers-and-sidecars/#put-it-into-practice), [Application volumes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/application-volumes/) |

```bash
dsoxlab run    k8s-challenge-composer-un-pod-multi-conteneurs
dsoxlab check  k8s-challenge-composer-un-pod-multi-conteneurs
dsoxlab submit k8s-challenge-composer-un-pod-multi-conteneurs
```
