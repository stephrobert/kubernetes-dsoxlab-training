# Remplacer une image criblée de failles, et le prouver par un second scan

Lab **CKS**, domaine *Supply Chain Security* (20 % de l'épreuve), compétence
« Scan images for known vulnerabilities ».

Le lab hérité demandait de consigner les constats dans des ConfigMaps dont le
seul contrôle était « la clé n'est pas vide » : n'importe quel texte passait.
Ici, ce qui se mesure est le RÉSULTAT du remplacement.

Le dernier test scanne les **deux** images, celle d'origine et celle que le
candidat a déployée, au même instant et avec la même base, puis exige
strictement moins de failles critiques dans la seconde. Un seuil fixe serait
faux dès la semaine suivante : la base s'enrichit tous les jours, et une image
irréprochable aujourd'hui compte des failles demain sans avoir changé d'un
octet. La comparaison, elle, reste vraie dans le temps.

Mesuré le 2026-09-16 : `nginx:1.21` porte **30 failles critiques et 227
élevées**, `nginx:1.27-alpine` en porte **2 et 35**.

Trivy est posé sur le nœud par **mise**, depuis `shared/outil-par-mise.yml`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Image Scanning](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |

```bash
dsoxlab run   cks-image-scanning-trivy
dsoxlab check cks-image-scanning-trivy
```

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
