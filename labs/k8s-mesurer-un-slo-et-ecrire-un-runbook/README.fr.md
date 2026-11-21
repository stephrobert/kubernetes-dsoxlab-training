# Écrire un runbook qui se rejoue, et mesurer le SLO d'une application

La leçon définit le runbook, le SLI, le SLO et le budget d'erreur. Ce cours les
met en pratique, avec des cas que la leçon ne montre pas : un runbook trompé par
la commande qu'il croyait sûre, puis corrigé ; un SLI et un budget calculés sur
un journal réel ; et le SLI d'une fenêtre courte, qui ne raconte pas la même
histoire que celui de la fenêtre entière.

Vous travaillez dans un namespace d'essai, `essai-slo`, avec une application
`vitrine`, et des fichiers d'essai dans votre répertoire. Le challenge porte sur
d'autres objets : vous le ferez seul, à la fin.

Page associée : [SRE et exploitation Kubernetes au quotidien](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/sre-exploitation-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-mesurer-un-slo-et-ecrire-un-runbook
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez l'application d'essai :

```bash
kubectl create namespace essai-slo; kubectl create deployment vitrine --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-slo; kubectl rollout status deployment/vitrine -n essai-slo --timeout=120s
```

```text
namespace/essai-slo created
deployment.apps/vitrine created
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
```

## 📒 Exercice 1 : un runbook trompé, puis corrigé

Un runbook doit pouvoir se rejouer : sur un service sain, il ne fait rien. Il
commence donc par regarder l'état. Voici une première version, qui fait
confiance à `kubectl rollout status`. Mettez `vitrine` en panne en lui retirant
tous ses réplicas, puis lancez le runbook :

```bash
cat > ~/essai-runbook.sh <<'RB'
#!/usr/bin/env bash
# Runbook d'essai, version 1 : il croit rollout status.
if kubectl -n essai-slo rollout status deployment/vitrine --timeout=10s >/dev/null 2>&1; then
  echo "vitrine disponible : rien à faire"; exit 0
fi
kubectl -n essai-slo scale deployment/vitrine --replicas=1
RB
chmod +x ~/essai-runbook.sh; kubectl -n essai-slo scale deployment/vitrine --replicas=0; ~/essai-runbook.sh; kubectl -n essai-slo get deployment vitrine
```

```text
deployment.apps/vitrine scaled
vitrine disponible : rien à faire
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   0/0     0            0           0s
```

Le runbook dit « rien à faire » alors que plus aucun Pod ne tourne : `0/0`.
`rollout status` répond « réussi » parce que le Deployment a autant de réplicas
disponibles que demandés, c'est-à-dire zéro. La commande qui semblait sûre ne
voit pas cette panne. La version 2 compte les réplicas disponibles :

```bash
cat > ~/essai-runbook.sh <<'RB'
#!/usr/bin/env bash
# Runbook d'essai, version 2 : il compte les réplicas disponibles.
dispo=$(kubectl -n essai-slo get deployment vitrine -o jsonpath='{.status.availableReplicas}')
if [ "${dispo:-0}" -ge 1 ]; then
  echo "vitrine disponible ($dispo) : rien à faire"; exit 0
fi
echo "aucun réplica disponible : remise à 1"
kubectl -n essai-slo scale deployment/vitrine --replicas=1
kubectl -n essai-slo rollout status deployment/vitrine --timeout=120s
RB
~/essai-runbook.sh
```

```text
aucun réplica disponible : remise à 1
deployment.apps/vitrine scaled
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
```

Cette fois, le runbook voit la panne et la répare. Rejouez-le sur le service
remis en marche :

```bash
~/essai-runbook.sh; kubectl -n essai-slo get deployment vitrine
```

```text
vitrine disponible (1) : rien à faire
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   1/1     1            1           1s
```

Il constate l'état sain et ne touche à rien. Un runbook se teste ainsi : sur la
panne qu'il doit traiter, puis sur un service qui marche.

## 📈 Exercice 2 : un SLI calculé sur un journal

Une sonde a vérifié `vitrine` chaque minute pendant un jour. Fabriquez son
journal : une ligne par minute, avec une panne de 9 minutes.

```bash
python3 -c "
import datetime
d = datetime.datetime(2026, 11, 20)
ko = set(range(600, 609))
print('horodatage,statut')
for m in range(1440):
    print(f'{d + datetime.timedelta(minutes=m):%Y-%m-%dT%H:%MZ},' + ('ko' if m in ko else 'ok'))
" > ~/essai-sonde.csv; wc -l < ~/essai-sonde.csv; grep -c ',ko' ~/essai-sonde.csv
```

```text
1441
9
```

1 441 lignes : l'en-tête et 1 440 minutes, dont 9 en panne. Le SLI de
disponibilité est la part des minutes où le service a répondu :

```bash
awk -F, 'NR>1 {t++; if ($2 == "ko") k++} END {printf "minutes %d, en panne %d, SLI %.2f %%\n", t, k, (t-k)/t*100}' ~/essai-sonde.csv
```

```text
minutes 1440, en panne 9, SLI 99.38 %
```

Pour un SLO de 99,9 % sur cette journée, le budget d'erreur vaut 0,1 % des
minutes :

```bash
awk -F, 'NR>1 {t++; if ($2 == "ko") k++} END {b = t*0.1/100; printf "budget %.2f min, consommé %d min, restant %.2f min\n", b, k, b-k}' ~/essai-sonde.csv
```

```text
budget 1.44 min, consommé 9 min, restant -7.56 min
```

Le budget est dépassé : une seule panne de 9 minutes consomme six fois ce que
l'objectif autorise en un jour. Un SLO de 99,9 % ne laisse qu'une minute et
demie par jour.

## 🔎 Exercice 3 : une fenêtre courte, une autre histoire

Mesurez maintenant le SLI sur les 20 minutes autour de la panne :

```bash
sed -n '597,616p' ~/essai-sonde.csv | awk -F, '{t++; if ($2 == "ko") k++} END {printf "20 minutes autour de la panne : SLI %.2f %%\n", (t-k)/t*100}'
```

```text
20 minutes autour de la panne : SLI 55.00 %
```

55 % sur 20 minutes, 99,38 % sur la journée : la même panne, deux chiffres. Un
SLI n'a de sens qu'avec sa fenêtre. La fenêtre courte dit qu'il faut agir
maintenant ; la fenêtre longue dit si l'objectif est tenu.

## 🧹 Nettoyage

Supprimez le namespace et les fichiers d'essai :

```bash
kubectl delete namespace essai-slo; rm -f ~/essai-runbook.sh ~/essai-sonde.csv
```

```text
namespace "essai-slo" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-mesurer-un-slo-et-ecrire-un-runbook
dsoxlab check k8s-mesurer-un-slo-et-ecrire-un-runbook
```

```text
╭─ Résultat : k8s-mesurer-un-slo-et-ecrire-un-runbook ─╮
│  0 / 100 pts                                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                     │
╰──────────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application tombée après une mise en
production, un runbook à écrire pour la prochaine fois, et 30 jours de sonde à
mesurer face à leur objectif.

```bash
dsoxlab run k8s-mesurer-un-slo-et-ecrire-un-runbook
dsoxlab challenge k8s-mesurer-un-slo-et-ecrire-un-runbook
```
