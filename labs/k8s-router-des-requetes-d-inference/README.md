# Route inference requests by replica load with the Gateway API Inference Extension

Guided lab of the lesson "Route inference traffic", level 6 "Advanced
networking" of the Kubernetes course (CKNE objective "Optimizing LLM
Traffic"). Group three replicas of a simulated model server in an
`InferencePool`, serve it through an Istio Gateway, and prove that the
requests follow the load of the replicas.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster, grown with the optional second worker `k8s-w2.lab`; the lab installs Istio 1.32 in ambient mode with the Inference Extension (CRDs v1.5.0), the endpoint picker v1.5.0 and the vLLM simulator `llm-d-inference-sim` v0.7.1 |
| Duration | about 35 minutes |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

The load of the saturated replica is **simulated**: the simulator publishes
fixed metrics (`--fake-metrics`), the only reliable way to keep a stable load
without a GPU. The endpoint picker reads them exactly as it would read those
of a real vLLM.

The `run` of this lab mounts `k8s-w2.lab` if it is not running yet, and joins it
to the cluster. The `cleanup.yaml` deletes the namespace `inference`,
uninstalls Istio with the CRDs of the Gateway API and of the Inference
Extension, then drains the second worker and removes it from the cluster.

```bash
dsoxlab run   k8s-router-des-requetes-d-inference
dsoxlab check k8s-router-des-requetes-d-inference
```
