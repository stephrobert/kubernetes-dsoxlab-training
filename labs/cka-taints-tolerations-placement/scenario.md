# Réserver un nœud : taint, tolérance et nodeSelector

## La situation

Le worker **`k8s-w1.lab`** vient de recevoir des disques SSD, et l'équipe
veut le **réserver à la production** : rien d'autre ne doit s'y planifier,
et l'application de production doit y aller, et nulle part ailleurs.

Vous êtes sur le control plane, avec `kubectl` configuré. Le namespace
**`lab`** existe.

## Ce que vous devez obtenir

1. Le nœud `k8s-w1.lab` porte le taint **`env=prod:NoSchedule`** et le
   label **`disktype=ssd`**.

2. Un Pod **`prod-app`** dans `lab`, image `nginx:1.27-alpine`, qui
   **tolère** ce taint et **exige** un nœud `disktype=ssd`. Il tourne sur
   `k8s-w1.lab`.

3. Un Pod **`dev-app`** dans `lab`, même image, sans tolérance ni
   sélecteur. Il tourne, mais **pas** sur `k8s-w1.lab`.

## Les repères utiles

Un taint et une tolérance ne font que **permettre** : un Pod qui tolère un
taint peut aller sur ce nœud, rien ne l'y oblige. Pour l'y **contraindre**,
il faut en plus lui demander un nœud, par un `nodeSelector` sur un label.
Les deux mécanismes se lisent dans le spec du Pod, et les tests les y
cherchent : un Pod épinglé sur le nœud par `nodeName` saute le scheduler et
le taint avec lui, ce n'est pas la réponse.

`kubectl describe node` montre les taints et les labels d'un nœud ;
`kubectl get pods -o wide` montre où chaque Pod a atterri.

## Comment vous saurez que c'est bon

Les tests lisent les taints et les labels du nœud, le nœud réel de chaque
Pod, et ce que le spec de `prod-app` déclare.

```bash
dsoxlab check cka-taints-tolerations-placement
```
