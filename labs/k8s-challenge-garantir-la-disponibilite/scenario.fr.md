# Garantir la disponibilité d'une application pendant une maintenance

## La situation

L'application **`paiement`**, dans le namespace **`paiement`** du cluster
kubeadm, encaisse les paiements de la boutique derrière son Service, nommé lui
aussi `paiement`. Elle tourne aujourd'hui en **un seul exemplaire**, et la
prochaine maintenance du worker **`k8s-w1.lab`** est prévue ce soir. Personne
ne veut que les paiements s'arrêtent pendant ce temps.

Ce que l'équipe sait de l'application, sur le port **80** :

- `/vivant.html` répond dès que le processus tourne ;
- l'application met ensuite une **vingtaine de secondes** à se mettre en
  route ; jusque-là, `/` ne sert pas sa page ;
- `/pret.html` ne répond qu'une fois la mise en route terminée.

Le responsable de l'exploitation veut aussi le **rapport de routine** que lit
l'équipe du matin. C'est un constat : ce qu'il signale appartient à d'autres
équipes, et vous n'y changez rien.

Vous êtes sur le control plane, avec `kubectl` configuré. Aucune procédure
n'est fournie : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. `paiement` tourne en **au moins trois exemplaires disponibles**.
2. **Un** budget de perturbation cible les Pods de `paiement` et garantit **au
   moins deux exemplaires disponibles** en toute circonstance, tout en laissant
   une maintenance possible.
3. Les exemplaires sont **répartis sur des nœuds différents**, autant que le
   cluster peut en offrir, par une règle déclarée dans la description de
   l'application.
4. Les **sondes de disponibilité et de vivacité** sont déclarées, et un
   exemplaire **ne reçoit du trafic qu'une fois prêt** : jamais pendant sa
   mise en route.
5. **Pendant l'évacuation d'un nœud**, `paiement` garde **au moins deux
   exemplaires disponibles**, et l'évacuation aboutit.
6. Le fichier **`~/routine/rapport.txt`** rend compte, tel que le cluster est
   vraiment :
   - des **nœuds**, chacun par son nom ;
   - des **Pods en erreur**, chacun par son nom ou par le nom de ce qui le
     gère ;
   - des **ressources orphelines** : les Jobs terminés qui restent ;
   - de l'**échéance** des certificats du plan de contrôle, telle que
     `kubeadm` ou `openssl` l'affichent, ou écrite `AAAA-MM-JJ`.

## Comment vous serez noté

Six états, à poids égal. Le seuil de réussite est de **70 sur 100**, et les
états **2 et 5** sont **bloquants** : le budget qui garantit le minimum, et le
minimum tenu pendant l'évacuation. Réussir les autres ne compense pas l'échec
de l'un d'eux.

Chaque check **agit sur le cluster**, et c'est dit ici : il évince un
exemplaire de `paiement` et regarde si son remplaçant reçoit du trafic avant
d'être prêt ; puis il **évacue lui-même `k8s-w1.lab`**, mesure les exemplaires
disponibles pendant l'évacuation, remet le nœud en service et répartit de
nouveau les exemplaires. Le rapport est comparé à l'état du cluster au moment
du check. Le retour se limite au verdict : réussi ou non, et le score.

```bash
dsoxlab check  k8s-challenge-garantir-la-disponibilite
dsoxlab submit k8s-challenge-garantir-la-disponibilite
```
