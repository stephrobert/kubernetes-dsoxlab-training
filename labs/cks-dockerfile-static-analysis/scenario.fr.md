# Corriger un Dockerfile que l'analyse statique refuse, sans changer l'application

## La situation

L'application **`inventaire`** a son Dockerfile en `/root/inventaire/`. Il
construit, l'image tourne, et c'est tout ce qu'on lui a demandé quand il a été
écrit.

L'équipe sécurité vient de brancher **Trivy** sur les fichiers de
configuration, et il refuse ce Dockerfile sur **cinq points**.

## Ce que vous devez obtenir

1. Vous avez **lancé l'analyse** et lu ce qu'elle reproche. Chaque constat
   porte un numéro et une section qui dit quoi écrire.

2. Les **cinq constats ont disparu**.

3. L'image **fait toujours la même chose** : elle part d'une image Node et
   lance `server.js`. Corriger en changeant de technologie répondrait à côté.

4. Le Dockerfile existe toujours. Le supprimer ferait taire l'analyse, ce qui
   n'est pas la même chose que la satisfaire.

## Les repères utiles

`trivy config <répertoire>` analyse les fichiers de configuration qu'il y
trouve, Dockerfile compris. C'est le même outil que pour les images, employé
en amont : là on mesure ce qu'une image **contient**, ici ce que sa recette
**promet**.

Chaque constat porte un identifiant de la forme `DS-0000`, une sévérité, un
intitulé, et une section `Resolution`. Lisez-la : elle dit exactement quoi
écrire, et elle évite de deviner.

Une image Alpine embarque beaucoup moins de paquets qu'une image basée sur
Debian, et son gestionnaire de paquets n'est pas le même. Changer de base
change donc aussi la ligne d'installation.

Un `HEALTHCHECK` dit à qui exécute l'image comment savoir si elle vit. Ce
n'est pas une option de confort : sans lui, un orchestrateur ne peut que
constater qu'un processus existe.

## Comment vous saurez que c'est bon

Le dernier test **relance l'analyse** et cherche les cinq constats par leur
**numéro**. Il ne compte pas : Trivy ajoute des règles à chaque version, et un
test qui exigerait « zéro constat » deviendrait rouge tout seul le jour où une
nouvelle règle sortirait, sans que votre Dockerfile ait changé d'une ligne.

```bash
dsoxlab check cks-dockerfile-static-analysis
```
