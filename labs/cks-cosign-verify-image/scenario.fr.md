# Signer une image, et prouver la signature en faisant refuser une autre

## La situation

Un **registre local** tourne sur le nœud, à l'adresse `localhost:5000`. Il
porte deux images, copiées telles quelles depuis Docker Hub :

- `localhost:5000/appli/web:1.0`, celle que l'équipe veut déployer ;
- `localhost:5000/appli/outil:1.0`, une autre image quelconque.

**Aucune n'est signée.** Rien ne distingue une image que votre équipe a
construite d'une image qu'un tiers aurait poussée à sa place.

`cosign` et `crane` sont installés sur le nœud.

## Ce que vous devez obtenir

1. Une **paire de clés** de signature, générée sur le nœud.

2. L'image `appli/web:1.0` est **signée** avec la clé privée, et sa signature
   se trouve dans le registre, à côté d'elle.

3. La **clé publique** est publiée dans le cluster, dans un ConfigMap nommé
   `cosign-pub-key` du namespace `chaine-signature`, sous la clé `cosign.pub`.

4. La clé privée **ne quitte pas le nœud** et n'entre dans aucun objet du
   cluster.

## Les repères utiles

`cosign generate-key-pair` écrit deux fichiers dans le répertoire courant.
L'outil demande un mot de passe de façon interactive ; la variable
d'environnement `COSIGN_PASSWORD` permet de le fournir sans dialogue, y
compris vide.

Signer **pousse** la signature dans le registre, dans le même dépôt que
l'image, sous un tag dérivé de son digest. C'est pour cela que ce lab monte un
registre local : aucun registre public n'accepterait cette écriture sans
identifiants.

`crane ls <dépôt>` liste les tags d'un dépôt, signatures comprises.

`cosign verify --key <clé publique> <image>` rend un code de retour : zéro si
la signature est valide, non nul sinon.

## Comment vous saurez que c'est bon

Le dernier test prend la clé publique **du ConfigMap**, comme le ferait un
tiers, et l'emploie sur les **deux** images. Elle doit accepter celle que vous
avez signée et refuser l'autre. Une vérification qui accepte tout ne prouve
rien, et c'est le cas le plus dangereux : une chaîne qui accepte tout
ressemble à une chaîne qui fonctionne.

```bash
dsoxlab check cks-cosign-verify-image
```
