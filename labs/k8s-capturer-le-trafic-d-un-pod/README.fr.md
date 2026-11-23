# Capturer le trafic d'un Pod

La leçon montre trois façons de capturer le trafic d'un Pod (l'interface
`cali` du nœud, `nsenter`, `kubectl debug`) et comment reconnaître un refus,
une perte ou un échec DNS. Ce cours ajoute ce qu'elle cite sans le montrer :
retrouver l'interface du nœud depuis l'intérieur du Pod, capturer côté
serveur pour voir qui envoie vraiment un RST, mesurer les délais entre
paquets, compter les requêtes DNS d'un nom court, et capturer sans rien
ajouter au Pod d'origine.

Vous travaillez dans le namespace `essai-capture`, avec un serveur `echo` et
une sonde `sonde` qui appelle un Service mal réglé. Le challenge porte sur
d'autres Pods et d'autres pannes, tirées au hasard : vous le ferez seul, à la
fin.

Page associée : [Capturer le trafic d'un Pod](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/capturer-trafic-pod/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le control plane du cluster
kubeadm, qui a deux workers, `k8s-w1.lab` et `k8s-w2.lab`. Posez les objets
d'essai : le serveur `echo` sur `k8s-w1`, qui écoute sur le port 5678, un
Service `echo-ferme` dont le port cible est 5690, où rien n'écoute, et la
sonde sur `k8s-w2`, qui appelle ce Service toutes les 2 secondes.

```bash
kubectl create namespace essai-capture; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: echo
  namespace: essai-capture
  labels:
    app: echo
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: echo
      image: hashicorp/http-echo:1.0.0
      args: ["-text=essai", "-listen=:5678"]
---
apiVersion: v1
kind: Service
metadata:
  name: echo-ferme
  namespace: essai-capture
spec:
  selector:
    app: echo
  ports:
    - port: 80
      targetPort: 5690
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: essai-capture
spec:
  nodeName: k8s-w2.lab
  containers:
    - name: curl
      image: curlimages/curl:8.22.0
      command: ["sh", "-c", "while true; do curl -sS -m 3 'http://echo-ferme/'; sleep 2; done"]
YAML
kubectl -n essai-capture wait --for=condition=Ready pod/echo pod/sonde --timeout=120s
kubectl -n essai-capture get pods -o wide; kubectl -n essai-capture get svc echo-ferme
```

```text
NAME    READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
echo    1/1     Running   0          1s    10.244.38.94    k8s-w1.lab   <none>           <none>
sonde   1/1     Running   0          1s    10.244.223.33   k8s-w2.lab   <none>           <none>
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
echo-ferme   ClusterIP   10.98.139.126   <none>        80/TCP    1s
```

Notez les deux adresses de Pods et la ClusterIP : les vôtres seront
différentes, remplacez-les dans les commandes qui suivent. Les sorties
montrées dans ce cours ont été relevées sur ces machines le 22 novembre 2026
(Kubernetes v1.37.2, tcpdump 4.99.4).

## 🔗 Exercice 1 : de l'intérieur du Pod à l'interface du nœud

Dans le Pod, l'interface s'appelle `eth0@ifN`, où `N` est l'index de l'autre
bout de la paire veth, sur le nœud. Cet index suffit à retrouver l'interface
`cali` sans connaître l'adresse du Pod. Sur `k8s-w2.lab`, entrez dans l'espace
réseau de la sonde, lisez l'index, puis cherchez l'interface qui le porte :

```bash
ssh k8s-w2.lab
id=$(sudo crictl ps --name curl -q --label io.kubernetes.pod.name=sonde | head -1)
pid=$(sudo crictl inspect --output go-template --template '{{.info.pid}}' "$id")
sudo nsenter -t "$pid" -n ip -br link show eth0
```

```text
eth0@if12        UP             c6:89:13:58:81:ce <BROADCAST,MULTICAST,UP,LOWER_UP>
```

L'index est 12. Cherchez-le parmi les interfaces du nœud, et comparez avec ce
que donne la route vers l'adresse de la sonde :

```bash
ip -o link | awk -F': ' '$1==12 {print $2}'
ip route get 10.244.223.33 | grep -o 'dev [^ ]*'
```

```text
cali84f4a66edb5@if2
dev cali84f4a66edb5
```

Les deux chemins mènent à la même interface. Le `@if2` du côté nœud renvoie à
l'index de `eth0` dans le Pod : chaque bout de la paire nomme l'autre. Cette
méthode marche aussi pour un Pod dont vous connaissez le conteneur mais pas
l'adresse.

## 🎯 Exercice 2 : qui envoie vraiment le RST

La leçon note qu'une capture côté client ne montre jamais l'émetteur réel
d'un RST. Capturez les deux côtés en même temps : la sonde sur `k8s-w2`, le
serveur sur `k8s-w1`. Quittez `k8s-w2` (`exit`), puis, depuis `k8s-cp`,
lancez la capture du serveur en arrière-plan et celle de la sonde aussitôt
après :

```bash
ssh k8s-w1.lab 'dev=$(ip route get 10.244.38.94 | grep -o "dev [^ ]*" | cut -d" " -f2); mkdir -p /tmp/essai-captures; sudo timeout 7 tcpdump -i $dev -nn -U -w /tmp/essai-captures/echo.pcap tcp 2>/dev/null' &
ssh k8s-w2.lab 'dev=$(ip route get 10.244.223.33 | grep -o "dev [^ ]*" | cut -d" " -f2); mkdir -p /tmp/essai-captures; sudo timeout 7 tcpdump -i $dev -nn -U -w /tmp/essai-captures/sonde.pcap tcp 2>/dev/null'; wait
ssh k8s-w2.lab 'sudo tcpdump -nn -r /tmp/essai-captures/sonde.pcap 2>/dev/null | head -2'
ssh k8s-w1.lab 'sudo tcpdump -nn -r /tmp/essai-captures/echo.pcap 2>/dev/null | head -2'
```

```text
21:22:42.082472 IP 10.244.223.33.45806 > 10.98.139.126.80: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
21:22:42.082551 IP 10.98.139.126.80 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
21:22:42.082057 IP 10.244.223.33.45806 > 10.244.38.94.5690: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
21:22:42.082068 IP 10.244.38.94.5690 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
```

Les deux premières lignes viennent de la sonde, les deux dernières du
serveur. Le `SYN` porte le même numéro de séquence (`1204700480`) des deux
côtés : c'est le même paquet. Côté sonde, le RST paraît venir du Service,
`10.98.139.126.80`. Côté serveur, il part du Pod `echo` lui-même,
`10.244.38.94`, sur le port **5690** : c'est le noyau du Pod qui refuse,
parce que rien n'écoute sur ce port. Le Service, lui, a bien fait son travail
en traduisant l'adresse. Les horloges des deux nœuds diffèrent de quelques
dixièmes de milliseconde : comparez les numéros de séquence, pas les heures.

## ⏱️ Exercice 3 : mesurer les délais, et filtrer à la relecture

La leçon dit qu'un refus est rapide et qu'une perte se lit à des envois
répétés. `tcpdump -ttt` affiche, à la place de l'heure, le temps écoulé
depuis le paquet précédent : la mesure se lit sans calcul. Relisez les deux
fichiers de l'exercice 2 :

```bash
ssh k8s-w2.lab 'sudo tcpdump -nn -ttt -r /tmp/essai-captures/sonde.pcap 2>/dev/null | head -4'
ssh k8s-w1.lab 'sudo tcpdump -nn -ttt -r /tmp/essai-captures/echo.pcap 2>/dev/null | head -2'
```

```text
 00:00:00.000000 IP 10.244.223.33.45806 > 10.98.139.126.80: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
 00:00:00.000079 IP 10.98.139.126.80 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
 00:00:02.004781 IP 10.244.223.33.45812 > 10.98.139.126.80: Flags [S], seq 143838984, win 64860, options [mss 1410,sackOK,TS val 2435130218 ecr 0,nop,wscale 7], length 0
 00:00:00.000179 IP 10.98.139.126.80 > 10.244.223.33.45812: Flags [R.], seq 0, ack 143838985, win 0, length 0
 00:00:00.000000 IP 10.244.223.33.45806 > 10.244.38.94.5690: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
 00:00:00.000011 IP 10.244.38.94.5690 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
```

Le RST revient en 79 µs côté sonde, et le serveur le renvoie en 11 µs : la
différence est le trajet entre les deux nœuds. Le nouveau `SYN` part
2,004 s plus tard, avec un autre port source (`45812`) et une autre séquence :
c'est un **nouvel appel** de la boucle de la sonde, pas une retransmission. Une
retransmission garde le même port et la même séquence.

Un filtre se pose aussi à la relecture : la capture garde tout, et vous ne
regardez que ce qui vous intéresse. Comptez les RST de la capture de la
sonde :

```bash
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/sonde.pcap 'tcp[tcpflags] & tcp-rst != 0' 2>/dev/null | wc -l"
```

```text
3
```

Trois RST en 7 secondes, un par appel de la sonde.

## 🔤 Exercice 4 : ce que coûte un nom court

Un Pod essaie chaque domaine de recherche de son `/etc/resolv.conf` avant le
nom lui-même. Un nom qui finit par un point est déjà complet : aucun domaine
ne s'y ajoute. Capturez le DNS de la sonde pendant qu'elle cherche un nom
inexistant, d'abord court, puis complet avec un point final. Remplacez
`cali84f4a66edb5` par l'interface trouvée à l'exercice 1 :

```bash
ssh k8s-w2.lab 'sudo mkdir -p /tmp/essai-captures; sudo timeout 12 tcpdump -i cali84f4a66edb5 -nn -U -w /tmp/essai-captures/dns-court.pcap udp port 53 2>/dev/null' &
sleep 2; time kubectl -n essai-capture exec sonde -- curl -sS -m 8 'http://inconnu-essai/'; wait
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/dns-court.pcap 2>/dev/null | grep 'A? inconnu' | cut -d' ' -f3-"
```

```text
curl: (6) Could not resolve host: inconnu-essai
command terminated with exit code 6

real	0m5.077s
user	0m0.029s
sys	0m0.013s
10.244.223.33.32952 > 10.96.0.10.53: 10690+ A? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.34159 > 10.96.0.10.53: 15310+ AAAA? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.38577 > 10.96.0.10.53: 6114+ A? inconnu-essai.svc.cluster.local. (49)
10.244.223.33.46852 > 10.96.0.10.53: 43755+ AAAA? inconnu-essai.svc.cluster.local. (49)
10.244.223.33.51030 > 10.96.0.10.53: 13124+ A? inconnu-essai.cluster.local. (45)
10.244.223.33.42744 > 10.96.0.10.53: 27261+ AAAA? inconnu-essai.cluster.local. (45)
10.244.223.33.34637 > 10.96.0.10.53: 36231+ A? inconnu-essai.lab. (35)
10.244.223.33.50576 > 10.96.0.10.53: 38082+ AAAA? inconnu-essai.lab. (35)
10.244.223.33.46638 > 10.96.0.10.53: 14922+ AAAA? inconnu-essai. (31)
10.244.223.33.45192 > 10.96.0.10.53: 13381+ A? inconnu-essai. (31)
10.244.223.33.45192 > 10.96.0.10.53: 13381+ A? inconnu-essai. (31)
10.244.223.33.46638 > 10.96.0.10.53: 14922+ AAAA? inconnu-essai. (31)
```

Douze requêtes pour un seul nom : une question A (IPv4) et une question AAAA
(IPv6) pour chacun des quatre domaines de recherche, puis le nom seul, envoyé
deux fois avec le même identifiant. Ce sont ces deux derniers envois, sans
réponse, qui portent la commande à 5 secondes. Refaites la mesure avec le nom
complet :

```bash
ssh k8s-w2.lab 'sudo timeout 12 tcpdump -i cali84f4a66edb5 -nn -U -w /tmp/essai-captures/dns-complet.pcap udp port 53 2>/dev/null' &
sleep 2; time kubectl -n essai-capture exec sonde -- curl -sS -m 8 'http://inconnu-essai.essai-capture.svc.cluster.local./'; wait
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/dns-complet.pcap 2>/dev/null | grep 'A? inconnu' | cut -d' ' -f3-"
```

```text
curl: (6) Could not resolve host: inconnu-essai.essai-capture.svc.cluster.local.
command terminated with exit code 6

real	0m0.083s
user	0m0.032s
sys	0m0.011s
10.244.223.33.33678 > 10.96.0.10.53: 4738+ A? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.39992 > 10.96.0.10.53: 18829+ AAAA? inconnu-essai.essai-capture.svc.cluster.local. (63)
```

Deux requêtes, et la commande entière, `kubectl exec` compris, rend la main en
0,08 s. Le message d'erreur est le même : seule la capture montre l'écart.
Quand une application met plusieurs secondes à échouer sur un nom, comptez ses
requêtes avant de soupçonner le serveur DNS.

## 🪞 Exercice 5 : capturer dans une copie du Pod

La leçon prévient qu'un conteneur éphémère reste inscrit dans le Pod.
`kubectl debug --copy-to` crée à la place une **copie** du Pod, à laquelle il
ajoute un conteneur de capture. L'original n'est pas touché :

```bash
kubectl -n essai-capture debug sonde --copy-to=sonde-copie \
  --image=nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70 \
  --container=capture -- tcpdump -i eth0 -nn -c 4 "tcp port 80"
sleep 30; kubectl -n essai-capture get pods -o wide
kubectl -n essai-capture logs sonde-copie -c capture | cut -c1-110
```

```text
NAME          READY   STATUS     RESTARTS     AGE     IP              NODE         NOMINATED NODE   READINESS GATES
echo          1/1     Running    0            2m16s   10.244.38.94    k8s-w1.lab   <none>           <none>
sonde         1/1     Running    0            2m16s   10.244.223.33   k8s-w2.lab   <none>           <none>
sonde-copie   1/2     NotReady   1 (8s ago)   35s     10.244.223.34   k8s-w2.lab   <none>           <none>
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
21:24:25.485615 IP 10.244.223.34.55756 > 10.98.139.126.80: Flags [S], seq 2662910559, win 64860, options [mss
21:24:25.486074 IP 10.98.139.126.80 > 10.244.223.34.55756: Flags [R.], seq 0, ack 2662910560, win 0, length 0
21:24:27.491714 IP 10.244.223.34.55758 > 10.98.139.126.80: Flags [S], seq 3492833395, win 64860, options [mss
21:24:27.491836 IP 10.98.139.126.80 > 10.244.223.34.55758: Flags [R.], seq 0, ack 3492833396, win 0, length 0
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```

La copie rejoue la commande de la sonde, donc le même refus. Comparez ensuite
les conteneurs des deux Pods :

```bash
for p in sonde sonde-copie; do printf '%-12s containers=%s ephemeral=%s\n' $p "$(kubectl -n essai-capture get pod $p -o jsonpath='{.spec.containers[*].name}')" "$(kubectl -n essai-capture get pod $p -o jsonpath='{.spec.ephemeralContainers[*].name}')"; done
```

```text
sonde        containers=curl ephemeral=
sonde-copie  containers=curl capture ephemeral=
```

L'original n'a ni conteneur ajouté ni conteneur éphémère. La copie porte un
second conteneur ordinaire, `capture`. Deux limites, visibles dans la sortie :
la copie a **sa propre adresse** (`10.244.223.34`), donc vous capturez son
trafic à elle, pas celui de l'original. Et son conteneur `capture` redémarre
à chaque fin de `tcpdump` (`RESTARTS 1`, `1/2`), parce que la copie garde la
politique de redémarrage du Pod d'origine. Supprimez-la dès la capture lue.
Cette méthode convient quand la panne se reproduit à chaque démarrage, pas
pour un état que seul l'original a atteint.

## 🧹 Nettoyage

Supprimez le namespace d'essai, qui emporte la copie, puis les captures
laissées sur les deux workers :

```bash
kubectl delete namespace essai-capture --wait=true --timeout=120s
for n in k8s-w1.lab k8s-w2.lab; do ssh $n sudo rm -rf /tmp/essai-captures; done
```

```text
namespace "essai-capture" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge, avec de nouvelles pannes tirées au hasard. Il vous
demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-capturer-le-trafic-d-un-pod
dsoxlab check k8s-capturer-le-trafic-d-un-pod
```

```text
╭─ Résultat : k8s-capturer-le-trafic-d-un-pod ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : trois clients d'une boutique échouent, chacun pour
une raison différente. Capturez leur trafic et désignez la cause de chaque
échec, sans rien réparer.

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
dsoxlab challenge k8s-capturer-le-trafic-d-un-pod
```
