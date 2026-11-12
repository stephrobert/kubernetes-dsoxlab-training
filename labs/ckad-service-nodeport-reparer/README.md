# Repair a NodePort Service

**CKAD** lab, *Services and Networking* domain: "Use ClusterIP, NodePort,
LoadBalancer service types and endpoints". Guided lab of the "Services" lesson
of the Kubernetes course.

The `accueil` application runs and answers its name. Its NodePort Service has a
selector targeting no Pod, a wrong `targetPort`, and a NodePort drawn at random.
The learner repairs it, and the tests prove it through a real request to the
NodePort of each of the two nodes. The neighbour
[`ckad-expose-service`](../ckad-expose-service/) covers ClusterIP. LoadBalancer
stays out of the lab: without a provider, its external address stays
`<pending>`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the worker `k8s-w1.lab` is queried too |
| Duration | about 20 minutes |
| Companion lesson | [Services](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-service-nodeport-reparer
dsoxlab check ckad-service-nodeport-reparer
```
