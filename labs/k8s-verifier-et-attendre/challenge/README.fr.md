# Challenge : Prévisualiser avec diff, attendre avec wait

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
Dans le namespace **`paiements`**, l'application **`facturation`** tourne en
version 1, avec 2 réplicas. Ses fichiers sont dans le dossier
**`~/deploiement/`** : `facturation.yaml`, et **`migration.yaml`**, un Job de
migration qui n'a jamais été appliqué.

La version 2 :

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## 🎯 Ce que vous devez obtenir

1. Dans le dossier, `facturation.yaml` décrit la **version 2**, et **le
   cluster correspond au dossier** : les comparer ne montre aucune différence.
2. **Tous les Pods** de `facturation` tournent en version 2 et sont prêts
   (Ready), et le **Job `migration` est terminé**.
3. **`~/deploiement/releve.txt`** donne la **révision** où en est
   `facturation` une fois la version 2 déployée, telle que le cluster la
   donne :

   ```text
   revision-v2: <numéro>
   ```

4. **`~/deploiement/deployer.sh`**, exécutable, prend un dossier en argument.
   Il compare ce dossier au cluster, applique s'il y a des différences, puis
   attend la fin du déploiement. Il **sort en 0** quand rien ne diffère. Il
   **s'arrête en erreur, sans rien appliquer**, quand `kubectl diff` ne peut
   pas comparer le dossier.
5. Le même script **attend aussi chaque Job du dossier**. Il sort en 0 quand
   ils réussissent, et **s'arrête en erreur dès qu'un Job échoue**, sans
   attendre la fin d'un délai.

## 🧭 Les repères utiles

Regardez chaque changement avant de l'appliquer. Le code de sortie de
`kubectl diff` ne veut pas dire ce qu'on croit : un script en `set -e` qui
l'oublie s'arrête au mauvais moment.

Un Deployment peut se dire Available pendant que d'anciens Pods servent
encore : attendez la vraie fin du déploiement, pas seulement sa
disponibilité. Un Job qui échoue ne remplit jamais la condition de réussite :
attendre cette seule condition, c'est attendre tout le délai.

Un `kubectl apply` sur un dossier dont un objet est refusé applique quand même
les autres.

## ✅ Comment vous saurez que c'est bon

Les tests comparent votre dossier au cluster, lisent le relevé, vérifient
l'image de chaque Pod et l'état du Job. Puis ils lancent votre script quatre
fois : sur le dossier tel quel, sur une copie qui contient un objet refusé par
le serveur, et sur deux copies qui ajoutent un Job, l'un qui échoue, l'autre
qui réussit.

```bash
dsoxlab check k8s-verifier-et-attendre
```
