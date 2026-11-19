# Challenge: Restrict who can log into a worker node, and with what rights

## The situation

The second worker **`k8s-w2.lab`** was installed from an old server template.
You open a session on it from the control plane with `ssh k8s-w2.lab`, as your
account **`ansible`**, which has `sudo`.

On this node:

- SSH accepts **every account**, **by password**, and **root** may log in. The
  file `/etc/ssh/sshd_config.d/05-heritage.conf` comes from the old template;
- the on-call account **`stagiaire`** holds **every sudo right**, through two
  paths. Its only real need: read the kubelet status with
  `sudo /usr/bin/systemctl status kubelet`.

Two accounts administer the node and must keep access: **`ansible`**
(automation, and your session) and **`student`** (the human administrator).

## What you must achieve

1. Only members of the group **`k8s-admins`** open an SSH session on
   `k8s-w2.lab`. This group holds `ansible` and `student`, and **not**
   `stagiaire`.
2. sshd accepts **keys** only: no more password, and **root** does not log in.
3. `stagiaire` keeps its account, loses every other right, and may run
   `sudo /usr/bin/systemctl status kubelet` **without a password**, nothing
   more.

## Landmarks

A mistake in `AllowGroups` locks you out of the node. Keep your first session
**open** during the whole work, and close it only after a second login
succeeds. `sshd -t` checks the syntax before the reload, and a reload does not
cut open sessions.

`sudo sshd -T` shows the configuration **read from disk**. The running daemon
may keep another one: after a reload, `pgrep -a sshd` must show **a single**
`sshd -D [listener]` process. An old one, left from a restart, keeps the old
configuration and serves part of the connections. sshd reads the files of `sshd_config.d` in alphabetical order and
keeps the **first** value it reads for each keyword.

For sudo rights, `sudo -l -U stagiaire` shows everything an account may do,
whatever the source. Check a sudoers file with `visudo -cf` before putting it
in place: a broken file can take sudo away from every account.

Once the node is closed, also look at what the kubelet credentials allow, from
`k8s-w2.lab`: `sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf get
nodes`, then `get node k8s-w2.lab`. The Node authorizer lets it read its own
node only. This step is not graded.

## How you will know it works

The tests open real SSH sessions on `k8s-w2.lab` with a test key placed in
`stagiaire`, `student` and `ansible`, read `sshd -T`, and try the sudo rights
of `stagiaire`.

```bash
dsoxlab check cks-restreindre-l-acces-au-noeud
```

If you locked yourself out: `dsoxlab destroy --optional-hosts`, then
`dsoxlab run cks-restreindre-l-acces-au-noeud` brings up a fresh machine.
