# Make Falco raise an alert on a shell opened in a protected namespace

**CKS** lab, *Monitoring, Logging and Runtime Security* domain (20 % of the
exam), competency "Perform behavioral analytics to detect malicious
activities".

The rules shipped with Falco cover generic behaviours, not your context. This
lab asks for a rule of your own, under a fixed name and priority, limited to
one namespace, loaded on top of the shipped rules without changing them.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster, where Falco runs |
| Duration | about 25 minutes |
| Lesson | [Falco](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco/) (French) |

```bash
dsoxlab run   cks-falco-detecter-un-shell
dsoxlab check cks-falco-detecter-un-shell
```
