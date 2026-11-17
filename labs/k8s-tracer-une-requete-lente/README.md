# Trace a slow request through the Istio mesh

Guided lab of the lesson "Trace a slow request through the Istio mesh", level 6
"Advanced networking" of the Kubernetes course (CKNE). Send the spans of a
waypoint to an OpenTelemetry collector and Jaeger, find why none arrives, make
the application forward the trace context, and name the slow service from a
single trace.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster, grown with the optional second worker `k8s-w2.lab`; the lab installs Istio 1.32 in ambient mode, an OpenTelemetry collector contrib 0.165.0 and Jaeger 2.23.0 |
| Duration | about 40 minutes |
| Prerequisite | the lab `k8s-servir-une-gateway-en-https` (same mesh, same cluster) |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

The `run` of this lab mounts `k8s-w2.lab` if it is not running yet, and joins it
to the cluster. Each `run` brings Istio back to the lab's profile, which erases
a trace provider left by a previous attempt, and draws the slow service again.
The `cleanup.yaml` deletes the namespaces `boutique` and `observabilite`,
uninstalls Istio with its CRDs, then drains the second worker and removes it
from the cluster: the virtual machine stays up for the next lab that needs it.

```bash
dsoxlab run   k8s-tracer-une-requete-lente
dsoxlab check k8s-tracer-une-requete-lente
```
