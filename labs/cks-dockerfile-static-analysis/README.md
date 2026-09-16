# Fix a Dockerfile static analysis rejects, without changing the application

**CKS** lab, *Supply Chain Security* domain (20 % of the exam), competency
"Minimize base image footprint".

It is the upstream counterpart of `cks-image-scanning-trivy`, with the same
tool: there you measure what an image **contains**, here what its recipe
**promises**.

Measured on 2026-09-16 with Trivy 0.74.0: the starting Dockerfile carries
**five findings** (`latest` tag, running as root, port 22 exposed, no
`HEALTHCHECK`, `apt-get` without `--no-install-recommends`), and the fixed
version carries **none**.

The last test looks for the five findings by their **number**, not by a total.
A test demanding "zero findings" would go red on its own the day Trivy added a
rule, without the Dockerfile changing a line: the catalogue would announce a
regression that does not exist.

Another test refuses the deletion of the Dockerfile: an analysis with nothing
to analyse holds nothing against you, and that is the simplest way around a
test that counts.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-dockerfile-static-analysis
dsoxlab check cks-dockerfile-static-analysis
```

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
