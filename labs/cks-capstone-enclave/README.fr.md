# Capstone : ouvrir une enclave pour une équipe qui n'est pas de confiance

Capstone **CKS**. Il croise trois des six domaines de l'épreuve : *Minimize
Microservice Vulnerabilities* (20 %), *Cluster Hardening* (15 %) et *Cluster
Setup* (15 %), soit **50 %** du blueprint.

**Aucune des cinq exigences ne nomme un objet Kubernetes.** C'est ce qui
distingue un capstone d'un micro-lab : un lab appelé
`networkpolicy-default-deny` a déjà répondu à la moitié de la question avant
que le candidat n'ouvre un terminal. Ici, il faut décider **ce qu'il faut
poser**.

Seuil de réussite : **66 %**, soit quatre exigences sur cinq.

## Deux preuves actives, et pourquoi elles sont nécessaires

Deux des cinq tests ne relisent pas ce que le candidat a posé, ils **tentent
ce qui doit être refusé** :

- le test d'admission crée réellement un Pod privilégié dans l'enclave et
  exige que le cluster le rejette. Un label d'admission mal orthographié est
  accepté sans broncher par l'API, ne refuse rien, et se relit pourtant comme
  les autres ;
- le test réseau interroge le service depuis les deux témoins. Une
  NetworkPolicy dont le sélecteur ne désigne personne est un objet
  parfaitement valide qui ne protège rien.

Le test réseau porte aussi le piège le plus coûteux du capstone : « l'intrus
ne joint pas le coffre » serait vert **avant le travail**, pour la plus
mauvaise des raisons, le coffre n'existant pas encore. C'est en exigeant
d'abord que l'appelant déclaré passe que ce faux vert est écarté.

## Un détail du setup qui n'en est pas un

Le Pod témoin `autorise` est posé **dans** l'enclave, avant que le candidat
n'y impose quoi que ce soit. L'admission ne juge qu'à la **création** : un Pod
déjà là survit à la règle posée ensuite. Il est néanmoins écrit conforme au
niveau `restricted`, pour qu'un candidat qui le supprimerait puisse le recréer
à l'identique.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 45 minutes |
| Leçon jumelée | [Exercices CKS](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cks/exercices/) |

```bash
dsoxlab run   cks-capstone-enclave
dsoxlab check cks-capstone-enclave
```

Le `cleanup.yaml` reprend aussi les objets de **cluster** qu'un candidat
aurait pu poser : un ClusterRole laissé derrière fausserait le lab suivant, et
la photographie du validateur le voit.
