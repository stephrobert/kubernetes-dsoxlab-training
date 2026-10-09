# Kubernetes DevSecOps Training: CKA, CKAD and CKS labs

**Language:** [English](./README.md) · [Français](./README.fr.md)

[![CI](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml/badge.svg)](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/stephrobert/kubernetes-dsoxlab-training?label=OpenSSF%20Scorecard)](https://securityscorecards.dev/viewer/?uri=github.com/stephrobert/kubernetes-dsoxlab-training)
[![Plumber compliance](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training.svg)](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)

A catalogue of **verifiable labs and capstones** for the
[Kubernetes training](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/)
on Stéphane Robert's blog. Played by the
[dsoxlab](https://github.com/stephrobert/dsoxlab) CLI.

A **micro-lab** exercises one competency named by the blueprint, and says so in
its title. A **capstone** names none: it hands over a situation, a 66 % pass
mark like the exam, and leaves you to pick the tools.

**All three Kubernetes certifications are entirely hands-on.** The candidate
repairs or builds on a real cluster: they do not pick the right answer out of
four. A quiz prepares you for the vocabulary, not for the exam. This catalogue
gives the learner the means to **prove** they can do the work.

Every lab sets an initial state, states a goal, and validates by reading **the
state of the system**, never the commands typed.

## Getting started

```bash
uv tool install dsoxlab        # the CLI, an external tool

git clone https://github.com/stephrobert/kubernetes-dsoxlab-training.git
cd kubernetes-dsoxlab-training
ansible-galaxy collection install -r requirements.yml

export LAB_HOME=$PWD
dsoxlab use --provider kvm
dsoxlab provision

dsoxlab list-labs
dsoxlab run   cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```

`dsoxlab destroy` gives the machines back.

## The infrastructure: a vanilla kubeadm cluster

Two Ubuntu 24.04 VMs, the distribution the published kubeadm guide recommends:
a control plane, `k8s-cp.lab`, and a worker, `k8s-w1.lab`, reachable over `ssh`
from the control plane as in the exam. The foundation installs a **Kubernetes
1.37** cluster, the version the training teaches, with Calico as the CNI.

**Why not kind?** Because some facts cannot be proven inside a container. On a
kind node, the kubelet refuses an AppArmor Pod with
`Cannot enforce AppArmor: AppArmor is not enabled on the host`. The training
teaches on kind, this catalogue proves on machines.

## The catalogue

<!-- LABS:START -->

### The recommended path

This is the order in which the labs are meant to be played, as declared in `meta.yml`. It is a teaching progression, not the structure of the exam: it goes from what a cluster is made of to diagnosing it, and ends with the capstone, which assumes the rest has been played. The table further down answers the other question, the one about coverage: which blueprint domain does each lab exercise.

**CKA, Certified Kubernetes Administrator**

1. [`cka-static-pod`](labs/cka-static-pod/): Place a static Pod on a worker, without going through the API
2. [`cka-daemonset-all-nodes`](labs/cka-daemonset-all-nodes/): An agent on every node, including the control plane
3. [`cka-rbac-serviceaccount`](labs/cka-rbac-serviceaccount/): Give an application an identity: ServiceAccount, Role, RoleBinding
4. [`cka-taints-tolerations-placement`](labs/cka-taints-tolerations-placement/): Reserve a node: taint, toleration and nodeSelector
5. [`cka-node-affinity`](labs/cka-node-affinity/): Placing with nodeAffinity: required constraint and preference
6. [`cka-networkpolicy-isolate-db`](labs/cka-networkpolicy-isolate-db/): Isolate the database: only the backend gets in
7. [`cka-ingress-path-routing`](labs/cka-ingress-path-routing/): Route two applications on a single host, and prove each gets its own
8. [`cka-gateway-api-httproute`](labs/cka-gateway-api-httproute/): Route with the Gateway API, and watch the Gateway report itself programmed
9. [`cka-pv-pvc-storageclass`](labs/cka-pv-pvc-storageclass/): A persistent volume: PersistentVolume, PersistentVolumeClaim and a Pod that writes
10. [`cka-storageclass-provisionnement-dynamique`](labs/cka-storageclass-provisionnement-dynamique/): Get a volume no administrator created, and follow what becomes of it
11. [`cka-deployment-rollout-rollback`](labs/cka-deployment-rollout-rollback/): Roll back a stuck rollout, then ship the right version
12. [`cka-node-drain-cordon`](labs/cka-node-drain-cordon/): Drain a worker for maintenance, without cutting the service
13. [`cka-hpa-autoscaling`](labs/cka-hpa-autoscaling/): Scale out automatically with a HorizontalPodAutoscaler
14. [`cka-resourcequota-limitrange`](labs/cka-resourcequota-limitrange/): Cap a namespace without blocking those who forget to declare themselves
15. [`cka-troubleshoot-imagepullbackoff`](labs/cka-troubleshoot-imagepullbackoff/): Get a Pod out of ImagePullBackOff
16. [`cka-troubleshoot-crashloopbackoff`](labs/cka-troubleshoot-crashloopbackoff/): Get a Deployment out of CrashLoopBackOff
17. [`cka-kubectl-debug`](labs/cka-kubectl-debug/): Get inside a container with no shell using kubectl debug
18. [`cka-troubleshoot-dns`](labs/cka-troubleshoot-dns/): Restore the cluster's DNS resolution
19. [`cka-troubleshoot-networking`](labs/cka-troubleshoot-networking/): Restore traffic to a Service
20. [`cka-troubleshoot-node-notready`](labs/cka-troubleshoot-node-notready/): Bring a NotReady node back into the cluster
21. [`cka-troubleshoot-kubelet`](labs/cka-troubleshoot-kubelet/): Repair a kubelet that refuses to start
22. [`cka-troubleshoot-apiserver`](labs/cka-troubleshoot-apiserver/): Bring the API server back into service
23. [`cka-etcd-backup-restore`](labs/cka-etcd-backup-restore/): Back up etcd, then restore the cluster from a snapshot
24. [`cka-kubeadm-upgrade`](labs/cka-kubeadm-upgrade/): Upgrade a cluster one minor version, without interrupting what runs on it
25. [`cka-capstone-portail`](labs/cka-capstone-portail/): Capstone: bring the portal back, with nobody left to ask · **capstone**

**CKAD, Certified Kubernetes Application Developer**

1. [`ckad-pod-resources-labels`](labs/ckad-pod-resources-labels/): A two-container Pod, with budgets, labels and an annotation
2. [`ckad-configmap-secret-injection`](labs/ckad-configmap-secret-injection/): Inject configuration and secrets into a Pod
3. [`ckad-secret-injection-protection`](labs/ckad-secret-injection-protection/): Take a password out of a manifest, without the application noticing
4. [`ckad-probes-all-types`](labs/ckad-probes-all-types/): Three probes on one Pod: startup, liveness, readiness
5. [`ckad-init-container`](labs/ckad-init-container/): Wait for a dependency with an init container
6. [`ckad-multi-container-sidecar`](labs/ckad-multi-container-sidecar/): A native sidecar that tails the application logs
7. [`ckad-volumes-partage-entre-conteneurs`](labs/ckad-volumes-partage-entre-conteneurs/): Let one container read what another writes, and nothing else
8. [`ckad-expose-service`](labs/ckad-expose-service/): Expose a Deployment through a ClusterIP Service
9. [`ckad-security-context-hardened`](labs/ckad-security-context-hardened/): Harden a Pod with a securityContext
10. [`ckad-rbac-role-rolebinding`](labs/ckad-rbac-role-rolebinding/): Grant read-only access to Pods with RBAC
11. [`ckad-networkpolicy-ingress-egress`](labs/ckad-networkpolicy-ingress-egress/): Partition three tiers with ingress and egress NetworkPolicy
12. [`ckad-rolling-update-strategy`](labs/ckad-rolling-update-strategy/): Tune a rolling update: maxSurge and maxUnavailable
13. [`ckad-blue-green-deployment`](labs/ckad-blue-green-deployment/): Switch traffic from one version to the other: blue-green
14. [`ckad-kustomize-overlays`](labs/ckad-kustomize-overlays/): One Kustomize base and two overlays, dev and prod
15. [`ckad-helm-install-upgrade`](labs/ckad-helm-install-upgrade/): Install, upgrade and roll back with Helm 4
16. [`ckad-job-cronjob`](labs/ckad-job-cronjob/): A Job with parallel completions, and a CronJob
17. [`ckad-in-place-pod-vertical-scaling`](labs/ckad-in-place-pod-vertical-scaling/): Resize a Pod in place, without restarting it
18. [`ckad-troubleshoot-missing-configmap`](labs/ckad-troubleshoot-missing-configmap/): A Pod blocked by a ConfigMap that does not exist
19. [`ckad-troubleshoot-crashloop`](labs/ckad-troubleshoot-crashloop/): Three Pods in CrashLoopBackOff, three causes
20. [`ckad-capstone-boutique`](labs/ckad-capstone-boutique/): Capstone: ship the shop, from the specification alone · **capstone**

**CKS, Certified Kubernetes Security Specialist**

1. [`cks-apparmor-confiner-un-pod`](labs/cks-apparmor-confiner-un-pod/): Confine a Pod with an AppArmor profile
2. [`cks-seccomp-profile`](labs/cks-seccomp-profile/): Deny a system call to a container, and prove it from the inside
3. [`cks-pod-security-admission`](labs/cks-pod-security-admission/): Reject a privileged Pod at admission, with Pod Security Admission
4. [`cks-secure-existing-pod`](labs/cks-secure-existing-pod/): Take over a privileged Pod in production, without stopping its work
5. [`cks-security-context-immutable`](labs/cks-security-context-immutable/): Make a container immutable without bringing it down
6. [`cks-runtime-sandbox-gvisor`](labs/cks-runtime-sandbox-gvisor/): Isolate a Pod from the host kernel, and prove it by reading its version
7. [`cks-image-pinned-digest`](labs/cks-image-pinned-digest/): Pin an image by digest, and prove the tag is not enough
8. [`cks-validating-admission-policy`](labs/cks-validating-admission-policy/): Have the cluster itself reject an unpinned image, with no webhook
9. [`cks-image-scanning-trivy`](labs/cks-image-scanning-trivy/): Replace an image riddled with flaws, and prove it with a second scan
10. [`cks-cosign-verify-image`](labs/cks-cosign-verify-image/): Sign an image, and prove the signature by having another one refused
11. [`cks-dockerfile-static-analysis`](labs/cks-dockerfile-static-analysis/): Fix a Dockerfile static analysis refuses, without changing the application
12. [`cks-rbac-least-privilege`](labs/cks-rbac-least-privilege/): Take cluster-admin away from a service account, without stopping its work
13. [`cks-api-server-hardening`](labs/cks-api-server-hardening/): Close the API server profiler, without closing the API
14. [`cks-audit-log-policy`](labs/cks-audit-log-policy/): Record who reads Secrets, and only the metadata of everything else
15. [`cks-networkpolicy-default-deny`](labs/cks-networkpolicy-default-deny/): Deny everything, then reopen the strict minimum, DNS included
16. [`cks-istio-mtls-lockdown`](labs/cks-istio-mtls-lockdown/): Require mTLS in a mesh, and prove it with a client left outside
17. [`cks-ingress-tls`](labs/cks-ingress-tls/): Serve a site over HTTPS with its own certificate, not the controller's
18. [`cks-cis-benchmark-remediate`](labs/cks-cis-benchmark-remediate/): Bring down a CIS audit count, and prove it with a second audit
19. [`cks-capstone-enclave`](labs/cks-capstone-enclave/): Capstone: open an enclave for a team you do not trust · **capstone**

### Blueprint coverage

The same labs, grouped by the domain the exam names. This is the view that answers "what can I actually prove?", and it is deliberately not the order in which you should play them.

#### CKA, Certified Kubernetes Administrator

25 lab(s).

| Lab | Title | Blueprint domain | Duration | Validated | Companion lesson |
|---|---|---|---|---|---|
| [`cka-kubeadm-upgrade`](labs/cka-kubeadm-upgrade/) | Upgrade a cluster one minor version, without interrupting what runs on it | cluster-architecture | 40m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/) |
| [`cka-etcd-backup-restore`](labs/cka-etcd-backup-restore/) | Back up etcd, then restore the cluster from a snapshot | cluster-architecture-installation-configuration | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |
| [`cka-node-drain-cordon`](labs/cka-node-drain-cordon/) | Drain a worker for maintenance, without cutting the service | cluster-architecture-installation-configuration | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/) |
| [`cka-rbac-serviceaccount`](labs/cka-rbac-serviceaccount/) | Give an application an identity: ServiceAccount, Role, RoleBinding | cluster-architecture-installation-configuration | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/) |
| [`cka-static-pod`](labs/cka-static-pod/) | Place a static Pod on a worker, without going through the API | cluster-architecture-installation-configuration | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |
| [`cka-gateway-api-httproute`](labs/cka-gateway-api-httproute/) | Route with the Gateway API, and watch the Gateway report itself programmed | services-networking | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/) |
| [`cka-ingress-path-routing`](labs/cka-ingress-path-routing/) | Route two applications on a single host, and prove each gets its own | services-networking | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |
| [`cka-networkpolicy-isolate-db`](labs/cka-networkpolicy-isolate-db/) | Isolate the database: only the backend gets in | services-networking | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| [`cka-pv-pvc-storageclass`](labs/cka-pv-pvc-storageclass/) | A persistent volume: PersistentVolume, PersistentVolumeClaim and a Pod that writes | storage | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/) |
| [`cka-storageclass-provisionnement-dynamique`](labs/cka-storageclass-provisionnement-dynamique/) | Get a volume no administrator created, and follow what becomes of it | storage | 25m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |
| [`cka-kubectl-debug`](labs/cka-kubectl-debug/) | Get inside a container with no shell using kubectl debug | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| [`cka-troubleshoot-apiserver`](labs/cka-troubleshoot-apiserver/) | Bring the API server back into service | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/) |
| [`cka-troubleshoot-crashloopbackoff`](labs/cka-troubleshoot-crashloopbackoff/) | Get a Deployment out of CrashLoopBackOff | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| [`cka-troubleshoot-dns`](labs/cka-troubleshoot-dns/) | Restore the cluster's DNS resolution | troubleshooting | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |
| [`cka-troubleshoot-imagepullbackoff`](labs/cka-troubleshoot-imagepullbackoff/) | Get a Pod out of ImagePullBackOff | troubleshooting | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/) |
| [`cka-troubleshoot-kubelet`](labs/cka-troubleshoot-kubelet/) | Repair a kubelet that refuses to start | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |
| [`cka-troubleshoot-networking`](labs/cka-troubleshoot-networking/) | Restore traffic to a Service | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| [`cka-troubleshoot-node-notready`](labs/cka-troubleshoot-node-notready/) | Bring a NotReady node back into the cluster | troubleshooting | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |
| [`cka-daemonset-all-nodes`](labs/cka-daemonset-all-nodes/) | An agent on every node, including the control plane | workloads-scheduling | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/) |
| [`cka-deployment-rollout-rollback`](labs/cka-deployment-rollout-rollback/) | Roll back a stuck rollout, then ship the right version | workloads-scheduling | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |
| [`cka-hpa-autoscaling`](labs/cka-hpa-autoscaling/) | Scale out automatically with a HorizontalPodAutoscaler | workloads-scheduling | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/) |
| [`cka-node-affinity`](labs/cka-node-affinity/) | Placing with nodeAffinity: required constraint and preference | workloads-scheduling | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| [`cka-resourcequota-limitrange`](labs/cka-resourcequota-limitrange/) | Cap a namespace without blocking those who forget to declare themselves | workloads-scheduling | 25m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/) |
| [`cka-taints-tolerations-placement`](labs/cka-taints-tolerations-placement/) | Reserve a node: taint, toleration and nodeSelector | workloads-scheduling | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| [`cka-capstone-portail`](labs/cka-capstone-portail/) | Capstone: bring the portal back, with nobody left to ask | capstone, several domains | 45m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

#### CKAD, Certified Kubernetes Application Developer

21 lab(s).

| Lab | Title | Blueprint domain | Duration | Validated | Companion lesson |
|---|---|---|---|---|---|
| [`ckad-blue-green-deployment`](labs/ckad-blue-green-deployment/) | Switch traffic from one version to the other: blue-green | application-deployment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |
| [`ckad-helm-install-upgrade`](labs/ckad-helm-install-upgrade/) | Install, upgrade and roll back with Helm 4 | application-deployment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/) |
| [`ckad-kustomize-overlays`](labs/ckad-kustomize-overlays/) | One Kustomize base and two overlays, dev and prod | application-deployment | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/) |
| [`ckad-rolling-update-strategy`](labs/ckad-rolling-update-strategy/) | Tune a rolling update: maxSurge and maxUnavailable | application-deployment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |
| [`ckad-init-container`](labs/ckad-init-container/) | Wait for a dependency with an init container | application-design | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| [`ckad-job-cronjob`](labs/ckad-job-cronjob/) | A Job with parallel completions, and a CronJob | application-design | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/) |
| [`ckad-multi-container-sidecar`](labs/ckad-multi-container-sidecar/) | A native sidecar that tails the application logs | application-design | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| [`ckad-pod-resources-labels`](labs/ckad-pod-resources-labels/) | A two-container Pod, with budgets, labels and an annotation | application-design | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| [`ckad-volumes-partage-entre-conteneurs`](labs/ckad-volumes-partage-entre-conteneurs/) | Let one container read what another writes, and nothing else | application-design | 20m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/) |
| [`ckad-configmap-secret-injection`](labs/ckad-configmap-secret-injection/) | Inject configuration and secrets into a Pod | application-environment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/) |
| [`ckad-in-place-pod-vertical-scaling`](labs/ckad-in-place-pod-vertical-scaling/) | Resize a Pod in place, without restarting it | application-environment | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| [`ckad-rbac-role-rolebinding`](labs/ckad-rbac-role-rolebinding/) | Grant read-only access to Pods with RBAC | application-environment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| [`ckad-secret-injection-protection`](labs/ckad-secret-injection-protection/) | Take a password out of a manifest, without the application noticing | application-environment | 20m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |
| [`ckad-security-context-hardened`](labs/ckad-security-context-hardened/) | Harden a Pod with a securityContext | application-environment | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| [`ckad-probes-all-types`](labs/ckad-probes-all-types/) | Three probes on one Pod: startup, liveness, readiness | application-observability | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/) |
| [`ckad-troubleshoot-crashloop`](labs/ckad-troubleshoot-crashloop/) | Three Pods in CrashLoopBackOff, three causes | application-observability | 15m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| [`ckad-troubleshoot-missing-configmap`](labs/ckad-troubleshoot-missing-configmap/) | A Pod blocked by a ConfigMap that does not exist | application-observability | 10m | 2026-09-15 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| [`ckad-expose-service`](labs/ckad-expose-service/) | Expose a Deployment through a ClusterIP Service | services-networking | 10m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| [`ckad-networkpolicy-ingress-egress`](labs/ckad-networkpolicy-ingress-egress/) | Partition three tiers with ingress and egress NetworkPolicy | services-networking | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| [`cka-resourcequota-limitrange`](labs/cka-resourcequota-limitrange/) | Cap a namespace without blocking those who forget to declare themselves | workloads-scheduling | 25m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/) |
| [`ckad-capstone-boutique`](labs/ckad-capstone-boutique/) | Capstone: ship the shop, from the specification alone | capstone, several domains | 45m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckad/exercices/) |

#### CKS, Certified Kubernetes Security Specialist

19 lab(s).

| Lab | Title | Blueprint domain | Duration | Validated | Companion lesson |
|---|---|---|---|---|---|
| [`cks-api-server-hardening`](labs/cks-api-server-hardening/) | Close the API server profiler, without closing the API | cluster-hardening | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |
| [`cks-rbac-least-privilege`](labs/cks-rbac-least-privilege/) | Take cluster-admin away from a service account, without stopping its work | cluster-hardening | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| [`cks-cis-benchmark-remediate`](labs/cks-cis-benchmark-remediate/) | Bring down a CIS audit count, and prove it with a second audit | cluster-setup | 30m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |
| [`cks-ingress-tls`](labs/cks-ingress-tls/) | Serve a site over HTTPS with its own certificate, not the controller's | cluster-setup | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |
| [`cks-networkpolicy-default-deny`](labs/cks-networkpolicy-default-deny/) | Deny everything, then reopen the strict minimum, DNS included | cluster-setup | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| [`cks-pod-security-admission`](labs/cks-pod-security-admission/) | Reject a privileged Pod at admission, with Pod Security Admission | minimize-vulnerabilities | 15m | 2026-09-15 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |
| [`cks-runtime-sandbox-gvisor`](labs/cks-runtime-sandbox-gvisor/) | Isolate a Pod from the host kernel, and prove it by reading its version | minimize-vulnerabilities | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |
| [`cks-secure-existing-pod`](labs/cks-secure-existing-pod/) | Take over a privileged Pod in production, without stopping its work | minimize-vulnerabilities | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| [`cks-security-context-immutable`](labs/cks-security-context-immutable/) | Make a container immutable without bringing it down | minimize-vulnerabilities | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| [`cks-audit-log-policy`](labs/cks-audit-log-policy/) | Record who reads Secrets, and only the metadata of everything else | monitoring-logging | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |
| [`cks-istio-mtls-lockdown`](labs/cks-istio-mtls-lockdown/) | Require mTLS in a mesh, and prove it with a client left outside | monitoring-logging | 30m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/) |
| [`cks-cosign-verify-image`](labs/cks-cosign-verify-image/) | Sign an image, and prove the signature by having another one refused | supply-chain-security | 30m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| [`cks-dockerfile-static-analysis`](labs/cks-dockerfile-static-analysis/) | Fix a Dockerfile static analysis refuses, without changing the application | supply-chain-security | 20m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| [`cks-image-pinned-digest`](labs/cks-image-pinned-digest/) | Pin an image by digest, and prove the tag is not enough | supply-chain-security | 15m | 2026-09-15 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| [`cks-image-scanning-trivy`](labs/cks-image-scanning-trivy/) | Replace an image riddled with flaws, and prove it with a second scan | supply-chain-security | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |
| [`cks-validating-admission-policy`](labs/cks-validating-admission-policy/) | Have the cluster itself reject an unpinned image, with no webhook | supply-chain-security | 30m | 2026-09-17 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/) |
| [`cks-apparmor-confiner-un-pod`](labs/cks-apparmor-confiner-un-pod/) | Confine a Pod with an AppArmor profile | system-hardening | 25m | 2026-09-15 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |
| [`cks-seccomp-profile`](labs/cks-seccomp-profile/) | Deny a system call to a container, and prove it from the inside | system-hardening | 25m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/seccomp/) |
| [`cks-capstone-enclave`](labs/cks-capstone-enclave/) | Capstone: open an enclave for a team you do not trust | capstone, several domains | 45m | 2026-09-16 | [lesson](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cks/exercices/) |

Total: **64 lab(s)**. The validation column carries the date of the last run of `scripts/valider-labs.py`, which plays the lab in both directions and checks that it leaves no trace. A shippable lab is not a validated lab.

**Runtime validated: Kubernetes v1.37.0.** **Reference curriculum: CKA v1.35, CKAD v1.35, CKS v1.34** ([cncf/curriculum](https://github.com/cncf/curriculum)). The two move at different speeds: the labs run on a newer Kubernetes than the published exam curriculum, which is why they are stated separately rather than as one version.

<!-- LABS:END -->

## Contributing

The rules for writing a lab, the testing doctrine and the repository's traps
live in [`CONTRIBUTING.md`](CONTRIBUTING.md).

A lab is only validated once played **in both directions**, leaving no trace:

```bash
python3 scripts/valider-labs.py --lab <id>
```

The validator photographs the cluster, plays the lab, checks that the tests
return 0 before the work and 100 after the trainer's solution, cleans up,
replays, then compares the cluster to its photograph. A forgotten namespace
turns the lab RED: it is not that lab that would pay the price, it is the next
one. Every lab's result, with its date and Kubernetes version, is in
[`validation-labs.json`](validation-labs.json).

## What facing the cluster corrected in the lessons

Every lab is paired with a blog lesson, and writing the lab forces you to play
what the lesson claims. Four errors were found and fixed, two of which made a
procedure inoperative:

- the etcd restore procedure stopped the kubelet, which does not stop the etcd
  container: nothing was being restored;
- an etcd restore does not change the member identity on a kubeadm cluster,
  contrary to what was written, because it is recomputed from the peer URLs and
  the cluster token.

The training teaches, this catalogue proves: what it contradicts goes back to
the blog.

## License

Copyright (c) 2026 Stéphane Robert, https://blog.stephane-robert.info

This catalogue is published under the
[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE) license.
You may share and adapt it, including commercially, on one condition: credit
Stéphane Robert, link to the blog, and indicate whether you changed the
content, without suggesting that the author endorses your use.

The `LICENSE` file contains only the official text of the license, with no
added header: that is what allows GitHub to recognise it.
