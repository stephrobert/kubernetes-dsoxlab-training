# Capturer le trafic d'un Pod et désigner la cause de chaque échec

Lab guidé de la leçon « Capturer le trafic d'un Pod au niveau paquet »,
niveau 6 « Réseau avancé » de la formation Kubernetes (objectif CKNE
« Using Linux Tools (iptables, ip, tcpdump) for Packet-level Issues »). Trois
Pods clients échouent de trois façons différentes : capturez leur trafic avec
tcpdump, nsenter ou kubectl debug, et désignez chaque cause d'après les
paquets.

| | |
|---|---|
| Cible | `k8s-cp.lab`, le cluster kubeadm du catalogue (Calico), agrandi du second worker optionnel `k8s-w2.lab` |
| Durée | environ 40 minutes |
| Prérequis | les bases réseau de la piste CKA (réseau des Pods, Services, CoreDNS) |
| Page associée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/), en attendant la publication de la leçon |

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
dsoxlab check k8s-capturer-le-trafic-d-un-pod
```

## Ce que vous saurez faire

- Trouver l'interface côté hôte d'un Pod à partir de la route vers son
  adresse.
- Capturer dans l'espace réseau d'un Pod avec nsenter, ou depuis un
  conteneur éphémère avec kubectl debug.
- Distinguer, dans une capture, une connexion refusée, des paquets perdus et
  un échec DNS : un reset, un SYN renvoyé sans réponse, des réponses
  NXDomain.
