# Épreuve du niveau 3 : exposer, configurer et livrer une application

Épreuve de fin de niveau de la formation Kubernetes : d'après un cahier des
charges qui ne nomme aucun objet Kubernetes, livrez et remettez en état
l'application d'un festival. Routez deux applications web par hôte et chemin,
réparez un composant hérité après avoir consigné sa cause, isolez la base,
placez les charges sur un nœud réservé et sur des nœuds distincts, plafonnez
le namespace, mettez l'application à l'échelle sur une métrique, donnez-lui sa
propre identité et durcissez son conteneur. Notée sur l'état final : onze
critères de même poids, seuil 70, six critères critiques, aucun indice.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `capacite` (Kubernetes 1.37, un control plane et trois workers), espaces `festival`, `paiement` et `partenaires` |
| Durée | environ 120 minutes |
| Page associée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/) (la page de l'épreuve reste à publier) |

```bash
dsoxlab run    k8s-epreuve-livrer-une-application
dsoxlab check  k8s-epreuve-livrer-une-application
dsoxlab submit k8s-epreuve-livrer-une-application
```
