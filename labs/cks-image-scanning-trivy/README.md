# Replace an image riddled with flaws, and prove it with a second scan

**CKS** lab, *Supply Chain Security* domain (20 % of the exam), competency
"Scan images for known vulnerabilities".

The inherited lab asked for findings to be recorded in ConfigMaps whose only
check was "the key is not empty": any text passed. Here, what is measured is
the RESULT of the replacement.

The last test scans **both** images, the original and the one the candidate
deployed, at the same moment and with the same database, then requires
strictly fewer critical findings in the second. A fixed threshold would be
wrong within a week: the database grows daily, and an image beyond reproach
today counts flaws tomorrow without having changed a byte. The comparison
stays true over time.

Measured on 2026-09-16: `nginx:1.21` carries **30 critical and 227 high**
findings, `nginx:1.27-alpine` carries **2 and 35**.

Trivy is installed on the node by **mise**, from `shared/outil-par-mise.yml`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [Image Scanning](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |

```bash
dsoxlab run   cks-image-scanning-trivy
dsoxlab check cks-image-scanning-trivy
```

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
