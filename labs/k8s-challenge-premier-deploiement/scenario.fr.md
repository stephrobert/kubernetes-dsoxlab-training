# Livrer la vitrine et remettre le stock en marche

## La situation

La boutique tourne sur un cluster kind nommé **`boutique`**. On vous a confié
son kubeconfig, copié dans **`~/.kube/boutique.yaml`**, et votre `kubectl`
le connaît déjà. Mais quelqu'un l'a laissé réglé sur un ancien cluster.

Dans le namespace **`catalogue`**, le service **`stock`** ne démarre pas. Son
manifeste est dans **`~/boutique/stock.yaml`**. La vitrine, elle, reste à
livrer.

L'image de référence de la boutique est :

```text
nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## Ce que vous devez obtenir

1. Votre contexte `kubectl` actif désigne le cluster de la boutique, et son
   namespace par défaut est **`vitrine`**.

2. Un Deployment **`vitrine`**, dans le namespace `vitrine`, avec **trois
   réplicas disponibles** sur l'image de référence.

3. Un Service **`vitrine`** qui désigne ces trois Pods.

4. La vitrine **répond** en HTTP sur `http://vitrine.vitrine` depuis un Pod du
   cluster. *Exigence bloquante.*

5. Un fichier **`~/boutique/cause-stock.txt`** qui nomme la raison pour
   laquelle `stock` ne démarre pas et l'image fautive, **écrit avant toute
   réparation**.

6. `stock` tourne sur l'image de référence, **corrigée dans
   `~/boutique/stock.yaml`** et appliquée depuis ce fichier.

7. **`~/.kube/boutique.yaml`** n'est lisible que par vous. *Exigence
   bloquante.*

## Comment vous serez noté

Le challenge est noté sur l'**état final** du cluster et des fichiers, jamais
sur les commandes tapées. Le seuil est de 70 sur 100, et les deux exigences
bloquantes doivent réussir quel que soit le total. Aucune consigne pas à pas :
les leçons du module Fondamentaux ont tout enseigné.

Les sept exigences pèsent toutes autant. Quatre **indices** sont proposés, et
chacun retire des points du barème avant le calcul de la note : 2, 3, 5 puis
5, soit 15 au plus. Ils plafonnent la note sans jamais recaler un sans-faute :
avec les quatre, sept exigences réussies donnent 85 et six en donnent 73. Avec
cinq exigences réussies, la marge est nulle : 71 sans indice, 70 avec le
premier, encore reçu, mais 68 dès le deuxième, sous le seuil.

`dsoxlab check` montre les exigences encore en échec ; `dsoxlab submit` rend le verdict du challenge, et c'est lui qui applique le seuil et les exigences bloquantes.

```bash
dsoxlab check  k8s-challenge-premier-deploiement
dsoxlab submit k8s-challenge-premier-deploiement
```
