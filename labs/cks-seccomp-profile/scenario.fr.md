# Interdire un appel système à un conteneur, et le prouver de l'intérieur

## La situation

Dans le namespace **`confinement`**, le Pod **`temoin`** tourne sans aucune
restriction : comme tout conteneur par défaut, il peut demander au noyau ce
qu'il veut, y compris changer les permissions des fichiers.

L'équipe sécurité veut qu'une application sensible ne puisse **pas** appeler
la famille `chmod`, sans pour autant l'empêcher de fonctionner.

## Ce que vous devez obtenir

1. Un profil seccomp nommé **`restrict-chmod.json`**, déposé sur le nœud à
   l'endroit où le kubelet cherche les profils locaux. Il **autorise tout par
   défaut** et **refuse** la famille `chmod`.

2. Un Pod **`seccomp-pod`** dans `confinement`, image `busybox:1.37`, qui
   déclare ce profil et qui **tourne**.

3. Dans ce Pod, un `chmod` **échoue**, et tout le reste continue de
   fonctionner : créer un fichier, par exemple, doit toujours marcher.

4. Le Pod **`temoin`**, lui, n'est pas confiné et peut toujours appeler
   `chmod`. N'y touchez pas : c'est à lui qu'on compare.

## Les repères utiles

Un profil seccomp **n'est pas un objet Kubernetes**. C'est un fichier JSON sur
le nœud, que le kubelet lit dans un répertoire qu'il est seul à connaître, et
le chemin déclaré dans le Pod est **relatif** à ce répertoire.

Le champ `defaultAction` décide de ce qui arrive aux appels **non nommés**.
Refuser par défaut obligerait à énumérer les centaines d'appels dont un
conteneur a besoin pour seulement démarrer.

Une famille d'appels compte souvent plus d'un nom. `chmod` en est le meilleur
exemple : une bibliothèque C moderne passe par un autre appel du même groupe,
et ne filtrer que le premier ne protège de rien.

Un appel refusé par seccomp rend l'erreur **EPERM**, que le shell affiche
« Operation not permitted ».

## Comment vous saurez que c'est bon

Les tests lisent le profil sur le nœud, la définition du Pod, puis entrent
dans le conteneur. Le dernier est le seul qui prouve le confinement, et il
exerce **les deux côtés** : ce qui est interdit doit échouer, et ce qui reste
permis doit continuer. Un profil vide passerait les deux premiers tests ; un
profil qui refuse tout casserait le conteneur.

```bash
dsoxlab check cks-seccomp-profile
```
