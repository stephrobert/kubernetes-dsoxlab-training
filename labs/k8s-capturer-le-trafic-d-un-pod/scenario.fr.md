# Capturer le trafic d'un Pod et désigner la cause de chaque échec

## La situation

Dans le namespace **`boutique`**, trois applications clientes appellent
leur service toutes les deux secondes :

| Client | Service appelé |
|---|---|
| `commandes` | `catalogue` |
| `factures` | `paiement` |
| `livraisons` | `transport` |

Les trois échouent, chacune d'une façon différente, et leurs journaux ne
disent que `appel vers http://... en échec`. L'équipe soupçonne trois causes
différentes : une connexion **refusée**, des paquets **perdus** en route, ou
un nom **DNS** qui ne se résout pas. Personne ne sait quel client a quel
problème : les paquets le diront.

Vous êtes sur le control plane, `k8s-cp.lab`, avec `kubectl` configuré. Les
clients tournent sur les deux workers, `k8s-w1.lab` et `k8s-w2.lab`, et
`ssh k8s-w1.lab` ouvre une session sur un worker. `tcpdump` est installé sur
les trois nœuds.

## Ce que vous devez obtenir

1. Pour chaque client, une capture de son trafic, écrite avec `tcpdump -w`,
   rapatriée sur le control plane sous **`~/captures/<client>.pcap`**
   (`~/captures/commandes.pcap`, et ainsi de suite).
2. Un fichier **`~/captures/diagnostic.yaml`** qui désigne la cause de
   chaque échec, une ligne par client, avec `refus`, `perte` ou `dns` :

   ```yaml
   commandes: <cause>
   factures: <cause>
   livraisons: <cause>
   ```

3. **Rien de réparé.** Le diagnostic se contrôle sur les pannes telles que
   le setup les a laissées : une panne réparée fait échouer le contrôle.

## La méthode, pas à pas

1. **Trouvez le Pod et son nœud** :
   `kubectl -n boutique get pods -o wide`. Notez l'adresse de chaque Pod
   client et le nœud qui le porte.
2. **Choisissez une façon de capturer.** Trois chemins mènent aux mêmes
   paquets :
   - sur le nœud, sur l'**interface côté hôte** du Pod. Calico la nomme
     `cali` suivi de 11 caractères ; la route vers l'adresse du Pod la
     donne : `ip route get <ip-du-pod>` ;
   - sur le nœud, **dans l'espace réseau du Pod** : trouvez le PID de son
     conteneur avec `crictl ps` et `crictl inspect`, puis
     `nsenter -t <pid> -n tcpdump -i eth0 ...`. C'est le tcpdump du nœud
     qui sert, l'image du Pod n'en a pas besoin ;
   - depuis le control plane, avec un **conteneur éphémère** qui partage le
     réseau du Pod : `kubectl debug` avec une image qui contient tcpdump et
     le profil `netadmin`. Un conteneur éphémère reste inscrit dans le Pod
     après sa fin.
3. **Capturez assez longtemps** : un appel qui échoue sur le DNS met
   environ 5 s à abandonner. 20 s couvrent plusieurs appels. Écrivez la
   capture avec `-w`, et gardez tous les paquets : les requêtes DNS comme
   les paquets TCP comptent.
4. **Rapatriez la capture** sur le control plane :
   `scp k8s-w1.lab:/tmp/<fichier>.pcap ~/captures/<client>.pcap`.
5. **Lisez-la** : `tcpdump -nn -r ~/captures/<client>.pcap`. Pour chaque
   client, posez trois questions. Le nom s'est-il résolu ? Un SYN TCP
   est-il parti ? Qu'est-ce qui est revenu, et en combien de temps ?

## Comment savoir que c'est réussi

`dsoxlab check k8s-capturer-le-trafic-d-un-pod` lit vos captures sur le
control plane avec `tcpdump -r`. Chacune doit contenir des paquets de
l'adresse **actuelle** de son Pod : une capture d'un `dsoxlab run`
précédent nomme une adresse qui n'existe plus. Chacune doit aussi contenir
les paquets qui prouvent la panne de son client. Le contrôle lit ensuite
les trois pannes dans les objets du cluster et les compare à votre
diagnostic.

Les pannes sont tirées au hasard à chaque `dsoxlab run` : un diagnostic ne
se reporte pas d'un passage à l'autre.
