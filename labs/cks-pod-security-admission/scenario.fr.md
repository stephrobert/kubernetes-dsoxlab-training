# Refuser un Pod privilégié à l'admission, avec Pod Security Admission

## La situation

Le namespace **`secure-ns`** accepte tout. Un Pod y tourne déjà, **`laxiste`**,
et il le prouve : il partage le namespace PID de l'hôte et son conteneur
tourne en root. Personne ne l'a empêché.

L'équipe sécurité veut que le cluster **refuse ce genre de Pod au moment où on
le demande**, et non qu'on le découvre après coup dans un audit.

## Ce que vous devez obtenir

1. Le namespace `secure-ns` applique le standard **`restricted`** dans les
   trois modes : celui qui **bloque**, celui qui **avertit** et celui qui
   **enregistre**.

2. Un Pod qui viole le standard est **refusé à l'admission**. Vous n'avez pas
   besoin de le créer pour le vérifier, et il vaut mieux ne pas le faire.

3. Un Pod **`conforme`** tourne dans `secure-ns`, avec l'image
   `busybox:1.37`, et il satisfait le standard restricted : utilisateur non
   root, aucune escalade de privilèges, toutes les capabilities retirées, et
   un profil seccomp déclaré.

4. Le Pod `laxiste`, lui, **continue de tourner**. N'y touchez pas : ce qu'il
   devient après l'activation du standard fait partie de ce que ce lab
   enseigne.

## Les repères utiles

Le standard s'active par des **labels sur le namespace**, pas par un objet
dédié. Les trois modes sont indépendants et peuvent viser des niveaux
différents.

`kubectl apply --dry-run=server` envoie l'objet à l'API server, qui le fait
passer par **toute la chaîne d'admission**, puis ne l'écrit pas. C'est la
façon propre de vérifier qu'une règle refuse quelque chose sans salir le
cluster, et c'est plus fiable qu'un `--dry-run=client`, qui ne quitte jamais
votre poste.

Le standard `restricted` exige quatre choses d'un conteneur, et le message de
refus les nomme une par une quand elles manquent.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster. Le dernier est le seul qui prouve
l'admission : il soumet un Pod interdit, qui doit être refusé, **et** un Pod
conforme, qui doit être accepté. Une politique qui refuse tout échouerait
aussi.

```bash
dsoxlab check cks-pod-security-admission
```
