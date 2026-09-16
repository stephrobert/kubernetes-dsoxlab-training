# Retirer cluster-admin à un compte de service, sans le priver de son travail

## La situation

Dans le namespace **`equipe-dev`**, l'application `portail-dev` tourne avec le
compte de service **`dev-sa`**. Ce compte est lié à **`cluster-admin`** par le
ClusterRoleBinding `dev-admin-binding` : quelqu'un a eu besoin que ça marche,
et l'affaire a été oubliée.

Rien n'est en panne. C'est précisément ce qui rend ce droit difficile à
reprendre : personne ne se plaint, et le jour où ce compte est compromis, tout
le cluster l'est avec lui.

L'audit demande de ramener `dev-sa` au **strict nécessaire**, sans casser
l'application.

## Ce que vous devez obtenir

1. **`dev-sa` n'est plus administrateur du cluster.** Le raccourci qui lui
   donnait ce pouvoir n'existe plus.

2. **Le compte garde de quoi travailler dans son namespace** : lire et écrire
   les Pods, les Deployments et les Services de `equipe-dev`. Son application
   s'en sert, elle doit continuer.

3. **Il ne peut plus lire les Secrets** de son propre namespace, `jeton-de-paiement`
   compris.

4. **Son pouvoir s'arrête à son namespace.** Il ne voit rien dans
   `kube-system`, ni ailleurs dans le cluster.

5. Le droit accordé est **porté par le namespace**, pas par un objet de
   cluster. Un droit qui vaut partout n'est pas un droit borné.

## Les repères utiles

Un droit ne se lit pas dans un manifeste, il se **demande à l'API server**.
`kubectl auth can-i` répond par oui ou par non, et son option `--as` permet de
poser la question **au nom de quelqu'un d'autre** : c'est ainsi qu'on vérifie
ce qu'un compte peut faire sans avoir à s'y connecter.

Un compte de service se nomme, dans une demande d'autorisation,
`system:serviceaccount:<namespace>:<nom>`.

Deux objets lient un sujet à des droits, et la différence est exactement le
sujet de ce lab : l'un vaut dans **un** namespace, l'autre dans **tout** le
cluster. Supprimer le second et le recréer sous un autre nom ne change rien.

## Comment vous saurez que c'est bon

Les tests ne lisent pas vos manifestes : ils posent les questions à l'API
server au nom de `dev-sa`, et comparent les réponses. Celui qui compte
vérifie les deux sens dans la même mesure : ce que le compte doit pouvoir
faire, et ce qu'il ne doit plus pouvoir faire. Un droit retiré à tout le monde
échouerait tout autant qu'un droit laissé entier.

```bash
dsoxlab check cks-rbac-least-privilege
```
