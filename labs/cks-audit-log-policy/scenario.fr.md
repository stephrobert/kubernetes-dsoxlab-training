# Enregistrer qui lit les Secrets, et seulement les métadonnées du reste

## La situation

Le cluster ne garde **aucune trace** de qui lit quoi. Un Secret consulté par
un compte compromis ne laisse rien derrière lui : ni l'heure, ni l'auteur, ni
même le fait que la lecture a eu lieu.

Dans le namespace **`coffre`**, le Secret **`dossier-medical`** attend d'être
lu. L'équipe conformité veut pouvoir répondre à la question « qui a lu ce
Secret, et quand ? », sans pour autant recopier tout le trafic du cluster sur
le disque.

## Ce que vous devez obtenir

1. L'API server applique une **politique d'audit** qui distingue deux cas :
   les accès aux **Secrets** sont enregistrés avec le **corps complet** de la
   requête et de la réponse ; **tout le reste** ne l'est qu'au niveau des
   **métadonnées**.

2. Le journal d'audit est écrit dans un fichier **du nœud**, à un emplacement
   qui survit au redémarrage du Pod de l'API server.

3. **L'API server répond toujours** une fois la modification faite. C'est la
   partie qui se rate le plus souvent, et le lab la mesure.

4. Le journal contient **réellement** la trace d'une lecture de Secret, au bon
   niveau, et celle d'une lecture banale, au niveau des métadonnées seulement.

## Les repères utiles

La politique d'audit n'est **pas un objet Kubernetes**. C'est un fichier du
nœud, que l'API server lit **au démarrage** : il faut donc qu'il redémarre
pour la prendre en compte, et c'est le kubelet qui s'en charge dès que le
manifeste statique change.

L'API server est un **Pod**. Il ne voit du nœud que ce qu'on lui montre :
donner un chemin de fichier dans un flag ne suffit pas, encore faut-il que ce
chemin soit monté dans le conteneur. C'est la cause de presque toutes les
pannes sur ce sujet, et `crictl logs` sur le conteneur `kube-apiserver` la
nomme en une ligne.

Une politique est une **liste ordonnée** de règles. L'API server retient la
**première** qui correspond à la requête, et ignore les suivantes.

Quatre niveaux existent, du plus discret au plus bavard : `None`, `Metadata`,
`Request`, `RequestResponse`.

## Comment vous saurez que c'est bon

Les tests lisent le nœud et le cluster. Le dernier déclenche deux opérations
réelles, une sensible et une banale, puis relit **ce que le cluster vient
d'écrire**. Une politique qui enregistrerait tout au niveau maximum échoue
autant qu'une politique absente.

```bash
dsoxlab check cks-audit-log-policy
```
