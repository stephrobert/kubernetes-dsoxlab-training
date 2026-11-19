# Challenge : Diagnostiquer deux Pods en échec

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Dans le namespace **`pods-en-panne`**, deux Pods créés à la main ne
marchent pas :

- **`image-fausse`** n'a jamais démarré ;
- **`plante`** démarre, puis s'arrête, encore et encore.

Le fichier **`~/pods-en-panne/releve.txt`** attend ce que vous lirez dans le
cluster.

## 🎯 Ce que vous devez obtenir

1. Après **`raison-image-fausse`** : la raison pour laquelle le conteneur de
   `image-fausse` attend.

2. Après **`code-sortie-plante`** : le code de sortie du conteneur de `plante`
   lors de son dernier arrêt.

3. **`image-fausse` tourne**, sur l'image **`nginx:1.30.5`**, et c'est **le
   même Pod** qu'au départ : vous avez corrigé son image sans le recréer.

4. **`plante` tourne sans redémarrer**, toujours sous le nom `plante` et sur la
   même image `busybox:1.38.0`. Seule sa commande a changé, pour une commande
   qui dure (une attente d'une heure, par exemple).

## 🧭 Les repères utiles

Commencez par la vue d'ensemble, puis descendez dans le détail.
`kubectl get pods -n pods-en-panne` montre les colonnes `STATUS` et
`RESTARTS`. `kubectl describe pod` montre l'état du conteneur, et ses
événements à la fin donnent la cause. Le code de sortie du dernier arrêt est
rangé dans l'état du Pod.

Les deux réparations ne se font pas de la même façon, et c'est le cœur du lab.
Une fois créé, un Pod ne se modifie presque plus. **Son image** fait partie des
rares champs qu'on peut changer sur un Pod existant. **Sa commande**, non :
pour la changer, récupérez le fichier YAML du Pod, corrigez-le, puis recréez le
Pod sous le même nom. Recréer `image-fausse`, ou garder `plante` sous un autre
nom, ne répond pas à la demande.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre fichier, puis l'état des deux Pods dans le cluster. Ils
vérifient aussi que `image-fausse` est bien le Pod du départ.

```bash
dsoxlab check k8s-diagnostiquer-un-pod
```
