# Donner à une application sa propre identité et le moindre droit

## La situation

L'équipe d'exploitation a installé deux outils dans le namespace
**`observatoire`** du cluster kubeadm :

- **`collecte`** doit lire le **journal des Pods** du namespace
  **`production`**, pour en extraire les incidents. Le Pod de production à
  surveiller s'appelle **`commandes`**.
- **`tableau`** sert une page statique et **n'appelle jamais l'API**.

Les deux tournent aujourd'hui sous le **compte par défaut** d'`observatoire`.
Pour « que ça marche », quelqu'un a donné à ce compte des droits étendus dans le
namespace, et `collecte` ne lit toujours pas le journal de `production`.

Vous êtes sur le control plane, avec `kubectl` configuré. Aucune procédure
n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. **`collecte`** tourne sous **sa propre identité**, nommée **`collecte`**, et
   non sous le compte par défaut.
2. Depuis le Pod de `collecte`, **avec son propre jeton**, lire le **journal du
   Pod `commandes`** de `production` aboutit.
3. **C'est tout** : l'identité `collecte` n'a **aucun autre droit, nulle part**.
   Ni créer, modifier ou supprimer quoi que ce soit dans `production`, ni lire
   ses Secrets, ni regarder un autre namespace, journaux compris, ni aucun droit
   sur le cluster.
4. Le Pod en marche de **`tableau`** ne porte **aucun jeton** : rien n'est monté
   dans `/var/run/secrets/kubernetes.io/serviceaccount`.
5. Le **compte par défaut** d'`observatoire` ne garde **aucun droit**, ni dans
   le namespace, ni ailleurs, au-delà de ce que Kubernetes donne à tout compte :
   s'interroger sur ses propres droits.
6. Le Pod de **`collecte`** est **durci** : il tourne en **non-root sous un UID
   numérique**, ne peut pas **élever ses privilèges**, a une **racine en lecture
   seule** et a retiré **toutes ses capabilities**. Durci, il lit toujours le
   journal de `production`.

## Comment vous serez noté

Six états, à poids égal. Le seuil est de **70 sur 100**, et les états **2 et
3** sont **bloquants** : la lecture du journal de `production`, et rien de plus.
Réussir les autres ne compense pas l'un d'eux manqué.

Les tests entrent dans le Pod de `collecte` et interrogent l'API avec son
jeton, puis font calculer par l'API les droits effectifs de chaque identité :
c'est l'application, et pas l'administrateur, qui doit avoir ces droits. Le
retour se limite au verdict : réussi ou non, et la note.

```bash
dsoxlab check  k8s-challenge-identite-et-droits-minimaux
dsoxlab submit k8s-challenge-identite-et-droits-minimaux
```
