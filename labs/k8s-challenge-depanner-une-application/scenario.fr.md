# Remettre en service une application en panne et son cluster

## La situation

Lundi, 8 h. Pendant le week-end, plusieurs personnes ont « réglé des choses »
sur le cluster kubeadm de la boutique, et ce matin plus rien ne marche :

- dans le namespace **`commerce`**, l'application **`api`** redémarre en
  boucle, et le Pod **`vitrine`** ne démarre jamais ;
- **`kubectl`** ne reçoit plus de réponse ;
- le worker **`k8s-w1.lab`** est sorti du cluster, et l'application
  **`entrepot`**, qui lui est réservée, est tombée avec lui.

Vous êtes sur le control plane. Comme à l'examen, `ssh k8s-w1.lab` ouvre une
session sur le worker. Aucune procédure n'est fournie : le module vous a appris
la méthode.

## Ce que vous devez obtenir

1. Le Deployment **`api`** a ses **deux replicas disponibles**.
2. **Aucun Pod** d'`api` ne redémarre plus en boucle.
3. `api` lit sa configuration là où la charte de l'équipe la place : la
   variable **`APP_CONFIG_PATH`** vaut **`/etc/config`**, l'application y trouve
   vraiment son fichier **`app.conf`**, et elle **répond** sur son port.
4. Le Pod **`vitrine`** tourne sur une **image nginx publique**, réellement
   tirée par le nœud, et **répond en HTTP**.
5. **Avant de réparer une panne**, vous écrivez sa cause dans un fichier de
   **`~/incident/`**, un par panne : **`api.txt`**, **`vitrine.txt`**,
   **`apiserver.txt`** et **`kubelet.txt`**. La cause vient de ce que vous avez
   lu (`describe`, les événements, les journaux) : elle **nomme ce qui ne va
   pas**, et pas seulement l'état qu'affiche Kubernetes. Ne touchez plus
   ensuite à ces fichiers : leur date est comparée au démarrage de ce qui a été
   réparé.
6. L'**API server** répond de nouveau, et son Pod tourne sans redémarrer en
   boucle.
7. Son **manifeste** ne porte plus le flag fautif, et autorise toujours les
   requêtes avec **`Node,RBAC`**.
8. **`k8s-w1.lab`** est **`Ready`**, et son kubelet tourne avec une
   configuration **valide**, qui garde l'adresse du DNS du cluster.
9. Le kubelet du worker est **actif**, et **redémarrera après un redémarrage**
   de la machine.
10. **`entrepot`** a de nouveau ses **trois replicas disponibles**, sur
    `k8s-w1.lab`.

Les réparations se font sur ce qui décrit l'application ou le nœud (le
Deployment, le manifeste, la configuration du service), pas en retirant ce qui
gêne : moins de replicas, une ligne supprimée ou une application déplacée sur
un autre nœud ne réparent rien.

## Comment vous serez noté

Dix états, à poids égal. Le seuil de réussite est de **70 sur 100**, et deux
états sont **bloquants** : les causes consignées avant les réparations (état
5) et l'API server remis en service (état 6). Réussir les autres ne compense
pas l'échec de l'un d'eux.

Les tests lisent le cluster par son API, l'état des services et les fichiers
des nœuds, et la date de vos fichiers de `~/incident/`. Le retour se limite au
verdict : réussi ou non, et le score.

```bash
dsoxlab check  k8s-challenge-depanner-une-application
dsoxlab submit k8s-challenge-depanner-une-application
```
