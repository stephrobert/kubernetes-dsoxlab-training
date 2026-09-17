# Sortir un mot de passe d'un manifeste, sans que l'application s'en aperçoive

## La situation

Dans le namespace **`paiement`**, le Deployment **`passerelle`** tourne et fait son
travail. Il reçoit son mot de passe de base de données par une variable
d'environnement **`DB_PASSWORD`**, dont la valeur est écrite **en clair dans le
manifeste**.

Ce manifeste est versionné, relu, copié dans des sauvegardes. Tout ce qui peut
le lire peut lire le mot de passe, y compris ce qui n'a aucune raison de le
connaître.

## Ce que vous devez obtenir

1. La valeur du mot de passe **n'apparaît plus** dans le manifeste du
   Deployment.

2. Elle est portée par un objet dédié du namespace.

3. L'application reçoit toujours son mot de passe dans la variable
   **`DB_PASSWORD`**, à l'identique.

4. La même valeur est **aussi** disponible sous forme de **fichier**, dans le
   répertoire `/etc/passerelle` du conteneur.

5. Le Deployment continue de tourner. Supprimer la variable serait une façon de
   faire disparaître la valeur du manifeste, mais pas celle qu'on vous demande.

Modifiez ce qui existe, ne remplacez pas le Deployment par un objet d'un autre
nom.

## Les repères utiles

L'objet qui porte une valeur sensible se crée en une commande, sans écrire de
YAML.

Il **n'est pas chiffré** : la valeur y est encodée, ce qui est un transport et
non une protection. Ce qu'il change, c'est qu'elle cesse de vivre au milieu de
la configuration de l'application.

Les deux chemins d'injection demandés ne se valent pas : une variable
d'environnement est figée pour la vie du processus, tandis qu'un fichier monté
est rafraîchi lorsque la valeur change.

Monté en volume, cet objet dépose chaque clé comme un fichier **portant son
nom**, sans extension ajoutée.

Un Pod qui référence un objet absent, ou une clé qui n'existe pas dedans, **ne
démarre pas** : il reste en `CreateContainerConfigError`, et
`kubectl describe pod` nomme le manquant dans ses events.

## Comment vous saurez que c'est bon

Le dernier test exerce **les deux côtés** : il vérifie que la valeur a quitté
le manifeste, puis qu'elle arrive quand même dans le conteneur, par la variable
et par le fichier. Séparées, ces deux moitiés ne mesureraient rien : supprimer
la variable ferait passer la première en cassant l'application, et la seconde
est déjà vraie avant votre intervention.

```bash
dsoxlab check ckad-secret-injection-protection
```
