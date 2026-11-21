# Faire baisser le compte d'un audit CIS, et le vérifier par un second audit

La leçon présente le CIS Benchmark et l'outil kube-bench qui le vérifie. Ici,
auditer et corriger le control plane est le challenge : ce cours audite un
**worker**. Il ajoute des cas que la leçon ne montre pas : kube-bench lancé en
Job sur un nœud précis, la cible `node`, la lecture du résumé, la liste des
écarts, puis un contrôle lu avec sa remédiation.

Vous travaillez dans un namespace d'essai, `essai-cis`, avec un Job à vous,
`essai-bench-noeud`. Le challenge a son propre Job : vous le ferez seul, à la
fin.

Page associée : [CIS Kubernetes Benchmark : auditer la sécurité de votre cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-cis-benchmark-remediate
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et kube-bench v0.16.0.

Lancez kube-bench en Job sur le worker `k8s-w1.lab`, avec la cible `node`.
kube-bench lit les fichiers du nœud : le Job les monte en lecture seule et
partage l'espace des processus du nœud (`hostPID`) pour voir le kubelet.

```bash
kubectl create namespace essai-cis; cat <<YAML | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: essai-bench-noeud
  namespace: essai-cis
spec:
  backoffLimit: 0
  template:
    spec:
      nodeName: k8s-w1.lab
      hostPID: true
      restartPolicy: Never
      containers:
        - name: kube-bench
          image: aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679
          command: [kube-bench, run, --targets, node]
          volumeMounts:
            - {name: var-lib-kubelet, mountPath: /var/lib/kubelet, readOnly: true}
            - {name: etc-systemd, mountPath: /etc/systemd, readOnly: true}
            - {name: lib-systemd, mountPath: /lib/systemd, readOnly: true}
            - {name: etc-kubernetes, mountPath: /etc/kubernetes, readOnly: true}
            - {name: usr-bin, mountPath: /usr/local/mount-from-host/bin, readOnly: true}
      volumes:
        - {name: var-lib-kubelet, hostPath: {path: /var/lib/kubelet}}
        - {name: etc-systemd, hostPath: {path: /etc/systemd}}
        - {name: lib-systemd, hostPath: {path: /lib/systemd}}
        - {name: etc-kubernetes, hostPath: {path: /etc/kubernetes}}
        - {name: usr-bin, hostPath: {path: /usr/bin}}
YAML
kubectl wait --for=condition=Complete job/essai-bench-noeud -n essai-cis --timeout=180s
```

```text
namespace/essai-cis created
job.batch/essai-bench-noeud created
job.batch/essai-bench-noeud condition met
```

## 📊 Exercice 1 : le résumé

Le rapport est dans les journaux du Pod du Job. Lisez le résumé :

```bash
kubectl logs job/essai-bench-noeud -n essai-cis | grep -A4 '^== Summary node'
```

```text
== Summary node ==
17 checks PASS
2 checks FAIL
6 checks WARN
0 checks INFO
```

17 contrôles réussis, 2 échecs, 6 avertissements. Un `WARN` est un contrôle
**manuel** : kube-bench ne sait pas trancher seul, c'est à vous de vérifier.

## 📋 Exercice 2 : les écarts

Listez les contrôles en échec ou en avertissement :

```bash
kubectl logs job/essai-bench-noeud -n essai-cis | grep -E '^\[(FAIL|WARN)\]'
```

```text
[FAIL] 4.1.1 Ensure that the kubelet service file permissions are set to 600 or more restrictive (Automated)
[WARN] 4.1.3 If proxy kubeconfig file exists ensure permissions are set to 600 or more restrictive (Manual)
[WARN] 4.1.4 If proxy kubeconfig file exists ensure ownership is set to root:root (Manual)
[FAIL] 4.1.9 If the kubelet config.yaml configuration file is being used validate permissions set to 600 or more restrictive (Automated)
[WARN] 4.2.9 Ensure that the --tls-cert-file and --tls-private-key-file arguments are set as appropriate (Manual)
[WARN] 4.2.12 Ensure that the Kubelet only makes use of Strong Cryptographic Ciphers (Manual)
[WARN] 4.2.13 Ensure that a limit is set on pod PIDs (Manual)
[WARN] 4.2.14 Ensure that the --seccomp-default parameter is set to true (Manual)
```

Les deux échecs portent sur des **droits de fichiers** : le fichier de
service du kubelet et son fichier de configuration sont trop ouverts.
`(Automated)` veut dire que kube-bench l'a vérifié lui-même, `(Manual)` qu'il
ne le pouvait pas.

## 🔧 Exercice 3 : un contrôle et sa remédiation

En fin de rapport, chaque écart a sa remédiation. Lisez celle du premier :

```bash
N=$(kubectl logs job/essai-bench-noeud -n essai-cis | grep -m1 -E '^\[(FAIL|WARN)\]' | awk '{print $2}'); echo "contrôle $N"; kubectl logs job/essai-bench-noeud -n essai-cis | sed -n '/^== Remediations node/,/^== Summary/p' | grep -A2 "^$N "
```

```text
contrôle 4.1.1
4.1.1 Run the below command (based on the file location on your system) on the each worker node.
For example, chmod 600 /lib/systemd/system/kubelet.service
```

La remédiation donne la commande, avec le chemin du fichier sur ce système.
Elle se joue sur le nœud audité, ici `k8s-w1.lab`. Une correction ne compte
qu'une fois vérifiée par un second audit.

## 🧹 Nettoyage

Supprimez le namespace d'essai, et le Job avec lui :

```bash
kubectl delete namespace essai-cis
```

```text
namespace "essai-cis" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-cis-benchmark-remediate
dsoxlab check cks-cis-benchmark-remediate
```

```text
╭─ Résultat : cks-cis-benchmark-remediate ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests         │
╰──────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : auditer le control plane, faire passer trois
contrôles qui partagent un même reproche, et le prouver par un second audit.

```bash
dsoxlab run cks-cis-benchmark-remediate
dsoxlab challenge cks-cis-benchmark-remediate
```
