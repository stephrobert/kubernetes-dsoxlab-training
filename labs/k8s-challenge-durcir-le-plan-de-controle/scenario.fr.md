# Corriger les écarts CIS d'un cluster, sans guidage

## La situation

Le cluster kubeadm sort d'une installation par défaut. L'équipe conformité y a
passé un audit CIS et veut deux choses avant la prochaine revue : les écarts
qui se corrigent sans changer l'architecture sont corrigés, et le cluster garde
la trace de **qui lit ses Secrets**.

Aujourd'hui, l'API server expose son profileur Go, rien n'est audité, et le
plan de contrôle porte les réglages que kubeadm écrit par défaut.

L'outil d'audit est prêt : le Job **kube-bench** est écrit sur le nœud, en
`/root/kube-bench-job.yaml`, et tourne dans le namespace **`conformite`**. Ce
namespace porte aussi le Secret **`jeton-de-paiement`**, celui que l'équipe
conformité veut voir tracé. Le setup a déjà lancé l'audit une fois et gardé son
nombre d'échecs.

Vous êtes sur le plan de contrôle, avec `kubectl` et `sudo`. Aucune procédure
n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. L'**API server** tourne avec son profileur **coupé**, vérifie qu'un jeton de
   compte de service présenté **existe toujours**, et refuse les versions de
   TLS sous un **plancher** que vous fixez.
2. Le profileur `/debug/pprof/` **ne répond plus**, et l'API server **répond
   toujours** aux requêtes ordinaires.
3. L'écart que l'audit CIS reproche à l'**API server**, au **controller
   manager** et au **scheduler**, contrôles **1.2.15**, **1.3.2** et
   **1.4.1**, est corrigé sur **les trois**.
4. kube-bench, **relancé**, passe ces trois contrôles et compte **moins
   d'échecs** qu'au départ.
5. Une **politique d'audit** en `/etc/kubernetes/audit-policy.yaml` enregistre
   les accès aux **Secrets en entier**, requête et réponse, et **tout le reste
   en métadonnées** seulement.
6. L'API server **tourne avec cet audit** : il lit cette politique et écrit son
   journal en `/var/log/kubernetes/audit.log` sur le nœud, et il répond
   toujours.
7. Le journal contient **réellement** la trace d'une lecture de Secret, en
   entier, et celle d'une lecture banale, en métadonnées seulement.

## Comment vous serez noté

Sept états, à poids égal. Le seuil est de **70 sur 100**, et les états **4 et
7** sont **bloquants** : l'audit relancé, et le journal qui trace. Réussir les
autres ne compense pas l'un d'eux manqué.

Les tests lisent les manifestes sur le nœud, relancent eux-mêmes kube-bench et
comparent son compte à celui que le setup a mesuré, puis font deux lectures
réelles et relisent ce que l'API server vient d'écrire. Le retour se limite au
verdict : réussi ou non, et la note.

```bash
dsoxlab check  k8s-challenge-durcir-le-plan-de-controle
dsoxlab submit k8s-challenge-durcir-le-plan-de-controle
```
