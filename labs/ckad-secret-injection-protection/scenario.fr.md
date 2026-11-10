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

2. Elle est portée par un **Secret** du namespace, comme contenu d'une de ses
   clés : relue et décodée, cette clé rend exactement le mot de passe. Le nom
   du Secret et celui de la clé sont à vous.

3. Le mot de passe n'est en clair **nulle part ailleurs** dans le namespace, et
   dans **aucun ConfigMap** en particulier. Déplacer la valeur du Deployment
   vers un ConfigMap la ferait quitter le manifeste sans rien protéger. Cet
   état est **contrôlé avec le précédent** : la valeur est dans un Secret, *et*
   elle n'est dans aucun ConfigMap. Pris seul, « dans aucun ConfigMap » est
   déjà vrai avant que vous commenciez, et ne mesure donc rien.

4. L'application reçoit toujours son mot de passe dans la variable
   **`DB_PASSWORD`**, à l'identique, et cette variable **tire sa valeur de ce
   Secret**, par référence. Là encore, la valeur seule n'est pas l'état
   demandé : cette variable porte **déjà** la bonne valeur au départ, écrite en
   clair dans le manifeste. Ce qui est mesuré, c'est son origine.

5. La même valeur est **aussi** disponible sous forme de **fichier**, dans le
   répertoire `/etc/passerelle` du conteneur. Le volume doit désigner ce
   Secret, et être monté à ce chemin exact.

6. Le Deployment continue de tourner : sa bascule va au bout, et le Pod qui est
   prêt est celui **né du gabarit modifié**, reconnaissable à la projection du
   Secret qu'il porte dans son propre spec. Un Pod tournait déjà avant que vous
   commenciez : « un Pod tourne » ne prouve donc rien à lui seul. Supprimer la
   variable serait une façon de faire disparaître la valeur du manifeste, mais
   pas celle qu'on vous demande.

Modifiez ce qui existe. Le Deployment est **mis à jour sur place**, en gardant
son nom et son historique : le supprimer puis le recréer est refusé, et
`kubectl rollout history` est ce qui montre la différence.

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

**Neuf tests, un par état ci-dessus**, chacun pesant le même neuvième de la
note. Deux d'entre eux sont la raison pour laquelle la liste est explicite :
l'un lit le contenu du Secret et le décode, l'autre balaye les ConfigMaps du
namespace. Ensemble, ils refusent le raccourci qui rendrait sinon la note
pleine : la valeur déplacée dans un ConfigMap et injectée de là, ce qui la
sort du manifeste et la laisse tout aussi lisible.

Supprimer la variable échoue toujours, comme auparavant : les tests qui entrent
dans le conteneur prouvent que l'application reçoit son mot de passe, par la
variable et par le fichier. Et les tests qui lisent le cluster disent **lequel**
des états manque, au lieu de s'arrêter au premier.

**Chacun des neuf refuse la situation de départ.** Trois d'entre eux passaient
auparavant avant tout travail : celui qui balaye les ConfigMaps, parce qu'une
absence est vraie avant qu'on commence ; celui qui voyait un Pod tourner, parce
que le setup en fait déjà tourner un ; et celui qui lisait `DB_PASSWORD` dans le
conteneur, parce qu'elle y portait déjà la bonne valeur, venue du manifeste.
Chacun exige maintenant l'état que le travail produit, et non un fait qui était
vrai au départ. Un test qui ne sait pas refuser ne mesure rien, et vous
donnerait un neuvième de la note pour la situation qu'on vous a remise.

```bash
dsoxlab check ckad-secret-injection-protection
```
