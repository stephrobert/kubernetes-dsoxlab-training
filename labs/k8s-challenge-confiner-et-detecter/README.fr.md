# Confiner un Pod et détecter une activité anormale, sans guidage

Challenge du module **Confiner et détecter** de la formation Kubernetes, dans
la section Mettre en pratique de la leçon « Runtime Sandboxes (gVisor, Kata) » :
un profil AppArmor à écrire et charger, un profil seccomp qui refuse `chmod`,
le TLS mutuel à exiger dans un maillage Istio, un namespace à fermer par défaut
sans couper son flux applicatif ni son DNS, un Pod à faire tourner dans un bac
à sable gVisor, et une règle Falco qui alerte sur un shell dans le namespace
protégé, et nulle part ailleurs. Seize exigences, seuil 70, trois bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab installe Falco 0.45.2 (pilote eBPF moderne), Istio 1.31 et gVisor, et pose les namespaces `coffre`, `maille`, `exterieur` et `donnees` |
| Durée | environ 75 minutes |
| Page associée | [Runtime Sandboxes, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |

```bash
dsoxlab run    k8s-challenge-confiner-et-detecter
dsoxlab check  k8s-challenge-confiner-et-detecter
dsoxlab submit k8s-challenge-confiner-et-detecter
```
