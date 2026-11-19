# Challenge : Sortir un mot de passe d'un manifeste, sans que l'application le remarque

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`paiement`**, le Deployment **`passerelle`**
tourne et fait son travail. Il reçoit son mot de passe de base de données par
la variable d'environnement **`DB_PASSWORD`**, dont la valeur est écrite **en
clair dans le manifeste**.

Ce manifeste est versionné, relu, copié dans des sauvegardes. Tout ce qui peut
le lire peut lire le mot de passe, même ce qui n'a aucune raison de le
connaître.

## 🎯 Ce que vous devez obtenir

1. Le mot de passe **n'apparaît plus** dans le manifeste du Deployment.

2. Il est rangé dans un **Secret** du namespace, comme valeur d'une de ses
   clés : relue et décodée, cette clé rend exactement le mot de passe. Le nom
   du Secret et celui de la clé sont à vous.

3. Le mot de passe n'est en clair **nulle part ailleurs** dans le namespace, et
   en particulier dans **aucun ConfigMap**. Le déplacer vers un ConfigMap le
   ferait sortir du manifeste sans rien protéger. Ce point est vérifié avec le
   précédent : la valeur est dans un Secret, *et* dans aucun ConfigMap.

4. L'application reçoit toujours son mot de passe dans la variable
   **`DB_PASSWORD`**, à l'identique. Cette variable **tire sa valeur du
   Secret**, par référence. Elle porte déjà la bonne valeur au départ : ce qui
   est vérifié, c'est d'où elle vient.

5. Le même mot de passe est **aussi** disponible en **fichier**, dans le
   dossier `/etc/passerelle` du conteneur. Le volume doit désigner ce Secret et
   être monté à ce chemin exact.

6. Le Deployment tourne toujours : la mise à jour va au bout, et le Pod prêt
   est celui **né du manifeste modifié**, qui monte le Secret. Un Pod tournait
   déjà au départ, donc « un Pod tourne » ne suffit pas. Supprimer la variable
   ferait disparaître la valeur du manifeste, mais ce n'est pas ce qui est
   demandé.

Modifiez ce qui existe. Le Deployment est **mis à jour sur place**, avec son
nom et son historique : le supprimer puis le recréer est refusé.
`kubectl rollout history` montre la différence.

## 🧭 Les repères utiles

Le Secret se crée en une commande, sans écrire de YAML.

Il **n'est pas chiffré** : la valeur y est encodée, ce qui permet de la
transporter, pas de la protéger. Ce qu'il change, c'est que la valeur ne vit
plus au milieu de la configuration de l'application.

Les deux façons d'injecter demandées ne se valent pas : une variable
d'environnement est figée pour toute la vie du processus, tandis qu'un fichier
monté est mis à jour quand la valeur change.

Monté en volume, un Secret dépose chaque clé dans un fichier **qui porte son
nom**, sans extension.

Un Pod qui demande un Secret absent, ou une clé qui n'y existe pas, **ne
démarre pas** : il reste en `CreateContainerConfigError`, et les événements du
Pod nomment ce qui manque.

## ✅ Comment vous saurez que c'est bon

Neuf tests, un par état demandé, chacun valant un neuvième de la note. Ils
lisent le Deployment, le Secret décodé et les ConfigMaps du namespace, puis ils
entrent dans le conteneur pour vérifier que l'application reçoit son mot de
passe, par la variable et par le fichier. Aucun ne passe sur la situation de
départ.

```bash
dsoxlab check ckad-secret-injection-protection
```
