# Capstone : remettre le portail en service, sans personne à qui demander

Premier **capstone CKA** du catalogue. Il ne vise pas une compétence du
blueprint, il en croise quatre : *Troubleshooting* (30 %), *Services and
Networking* (20 %), *Workloads and Scheduling* (15 %) et *Storage* (10 %),
soit 75 % de l'épreuve.

Un micro-lab annonce son sujet dans son titre. `cka-troubleshoot-dns` apprend
à réparer le DNS, et prévient que le problème est le DNS : la moitié de la
question est répondue avant que le candidat n'ouvre un terminal. Ici, le
namespace `production` contient **trois défauts indépendants** et rien ne dit
lesquels. Corriger le premier trouvé ne fait rien répondre.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 45 minutes |
| Seuil de réussite | 66 %, celui de l'examen CKA |
| Leçon jumelée | [Exercices CKA](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

```bash
dsoxlab run    cka-capstone-portail
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```

Huit tests, qui mesurent des effets et non des manifestes : le sélecteur
fautif se corrige côté Service comme côté Pods, et le stockage en créant un
volume comme en réécrivant la réclamation. Le dernier interroge le portail
depuis **chacun** des deux nœuds, comme la supervision le fera.

Écrit le 2026-09-15, puis validé par `scripts/valider-labs.py` : 0 avant le
travail, 100 après la solution du formateur, rejouable et sans trace.
