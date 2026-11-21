# Challenge : Écrire un runbook qui se rejoue, et mesurer le SLO d'une application

## La situation

Ce matin, l'équipe a mis en production une nouvelle image de l'application
**`catalogue`**, dans le namespace du même nom. Depuis, elle ne répond plus.
L'incident se reproduira : quelqu'un d'autre que vous devra le traiter, peut-être
la nuit, et il doit pouvoir le faire en lançant une seule commande.

Une sonde vérifie la disponibilité du service chaque minute. Elle a écrit ses
30 derniers jours dans **`/srv/catalogue/sonde.csv`** : une ligne par minute,
`ok` quand le service a répondu, `ko` sinon. L'équipe s'est fixé un objectif de
disponibilité (SLO) de **99,5 %** sur 30 jours.

## Ce que vous devez obtenir

1. L'application **`catalogue`** répond de nouveau, avec ses **deux** réplicas,
   sur sa **dernière bonne image**.

2. Un runbook exécutable, **`~/runbooks/catalogue-indisponible.sh`**, remet le
   service en marche quand la même panne se reproduit. Les tests le prouvent en
   recassant l'application de la même façon, puis en le lançant.

3. Lancé sur un service **qui marche**, ce runbook sort en **0** et **ne change
   rien**. Un runbook regarde l'état avant d'agir.

4. Un ConfigMap **`slo-catalogue`**, dans le namespace `catalogue`, consigne :
   - `sli` : la disponibilité mesurée sur les 30 jours du journal, en
     pourcentage à **deux décimales** (par exemple `99.62`) ;
   - `slo` : l'objectif, `99.5` ;
   - `budget-restant` : le budget d'erreur des 30 jours, moins les minutes de
     panne, en **minutes entières**. Il est négatif si le budget est dépassé.

## Les repères utiles

Un Deployment garde ses révisions précédentes : `kubectl rollout history` les
liste, et le statut de ses Pods dit pourquoi une révision ne démarre pas.

Le budget d'erreur, c'est ce que l'objectif autorise à manquer : avec un SLO de
99,5 %, il vaut 0,5 % de la fenêtre.

## Comment vous saurez que c'est bon

Les tests jouent votre runbook deux fois, sous votre compte : une fois après
avoir recassé l'application, une fois sur un service sain. Ils recalculent
ensuite le SLI et le budget depuis le tirage de la préparation : le nombre de
minutes en panne change à chaque passage.

```bash
dsoxlab check k8s-mesurer-un-slo-et-ecrire-un-runbook
```
