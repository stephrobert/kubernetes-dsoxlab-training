# Restrict who can log into a worker node, and with what rights

The lesson shows how to reserve SSH to a group and cut down the `sudo` rights
of an account. This course adds three moves it does not show: asking sshd
what it would decide for a given user, without reloading it; getting a badly
written sudoers file refused before it breaks `sudo`; and reading the actual
rights of an account, argument by argument.

You work on `k8s-w1.lab`, over `ssh` from the control plane, with a test
account and a test group. The challenge targets another node and other
accounts: you will do it on your own, at the end.

Related page: [Harden the nodes of a Kubernetes cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-restreindre-l-acces-au-noeud
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). `ssh` reaches the workers without a password.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2, Ubuntu 24.04 and OpenSSH 9.6.

First create the account `essai-visiteur` and the group `essai-astreinte` on
`k8s-w1.lab`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo groupadd -f essai-astreinte; sudo useradd -m -s /bin/bash essai-visiteur 2>/dev/null; id essai-visiteur'
```

```text
uid=1002(essai-visiteur) gid=1003(essai-visiteur) groups=1003(essai-visiteur)
```

## 🔍 Exercise 1: what sshd would do, without reloading it

`sshd -T` prints the configuration sshd would apply, once all its files are
read. It is the only reliable way to know it: sshd keeps the **first** value
it reads for a keyword, and the order of the files in `sshd_config.d/`
decides. Read the four settings that matter here:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo sshd -T | grep -E "^(passwordauthentication|permitrootlogin|allowgroups|allowusers)"'
```

```text
permitrootlogin without-password
passwordauthentication no
```

Neither `allowgroups` nor `allowusers` shows up: any account with a key can
get in. Add a restriction in a test file, have it checked by `sshd -t` (which
only reads the configuration), then ask sshd what it would decide for a given
connection with `-C`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'printf "AllowGroups essai-astreinte\n" | sudo tee /etc/ssh/sshd_config.d/90-essai.conf >/dev/null; sudo sshd -t; echo "sshd -t : code $?"; sudo sshd -T -C user=essai-visiteur,host=poste,addr=10.0.0.9 | grep -E "^allowgroups"'
```

```text
sshd -t : code 0
allowgroups essai-astreinte
```

`sshd -t` returns 0: the file parses, sshd would restart without error. `-C
user=...,host=...,addr=...` describes a connection, and sshd answers with the
rules that would apply to it. You test a rule before reloading the service,
so before risking locking yourself out.

Remove the test file and check the restriction is gone:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -f /etc/ssh/sshd_config.d/90-essai.conf; sudo sshd -T | grep -c "^allowgroups"'
```

```text
0
```

`grep -c` counts 0 lines (and returns code 1 when it finds nothing): the
configuration is back to its starting state, and sshd was never reloaded.

## 🛑 Exercise 2: a sudoers file refused before it does harm

A badly written file in `/etc/sudoers.d/` makes **every** `sudo` fail on the
machine, yours included. `visudo -c -f` checks a file without installing it.
Write a rule that lacks the colon after `NOPASSWD`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'echo "essai-visiteur ALL=(root) NOPASSWD /usr/bin/journalctl -u kubelet" > /tmp/essai-sudoers; sudo visudo -c -f /tmp/essai-sudoers'
```

```text
/tmp/essai-sudoers:1:66: syntax error
essai-visiteur ALL=(root) NOPASSWD /usr/bin/journalctl -u kubelet
                                                                 ^
```

`visudo` refuses, shows the line and returns code 1. Fix the rule, and install
it only if the check passes:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'echo "essai-visiteur ALL=(root) NOPASSWD: /usr/bin/journalctl -u kubelet" > /tmp/essai-sudoers; sudo visudo -c -f /tmp/essai-sudoers && sudo install -m 0440 /tmp/essai-sudoers /etc/sudoers.d/essai-visiteur'
```

```text
/tmp/essai-sudoers: parsed OK
```

`parsed OK`, then `install -m 0440` puts the file in place with the
permissions sudo requires. The `&&` makes sure a refused file never reaches
`/etc/sudoers.d/`.

## 🔐 Exercise 3: what the account can do with sudo

`sudo -l -U` lists the rights of an account, as sudo computes them from all
its files:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo -l -U essai-visiteur | tail -2'
```

```text
User essai-visiteur may run the following commands on k8s-w1:
    (root) NOPASSWD: /usr/bin/journalctl -u kubelet
```

A single rule: `journalctl -u kubelet`, without a password. Try it as is, then
with one more argument, then another command:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo -u essai-visiteur sudo -n /usr/bin/journalctl -u kubelet >/dev/null; echo "la ligne exacte : code $?"; sudo -u essai-visiteur sudo -n /usr/bin/journalctl -u kubelet -n 1 >/dev/null; echo "un argument de plus : code $?"; sudo -u essai-visiteur sudo -n /usr/bin/systemctl restart kubelet; echo "une autre commande : code $?"'
```

```text
la ligne exacte : code 0
sudo: a password is required
un argument de plus : code 1
sudo: a password is required
une autre commande : code 1
```

The exact line passes (code 0). With `-n 1` added, sudo refuses: a rule that
carries arguments allows **only** those arguments. That is what lets you give
a single command to an account, and it is also a trap: a rule that is too
precise refuses a legitimate use, and a rule without arguments
(`/usr/bin/journalctl`) would allow any option.

## 🧹 Clean-up

Remove the sudoers file, the test account and the test group:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -f /etc/sudoers.d/essai-visiteur /tmp/essai-sudoers; sudo userdel -r essai-visiteur 2>/dev/null; sudo groupdel essai-astreinte; id essai-visiteur 2>&1'
```

```text
id: ‘essai-visiteur’: no such user
```

`id` no longer finds the account: `k8s-w1.lab` is back to its starting state.

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-restreindre-l-acces-au-noeud
dsoxlab check cks-restreindre-l-acces-au-noeud
```

```text
╭─ Result: cks-restreindre-l-acces-au-noeud ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a worker where every account logs in over
SSH, with a password, and an on-call account that holds far too many rights.

```bash
dsoxlab run cks-restreindre-l-acces-au-noeud
dsoxlab challenge cks-restreindre-l-acces-au-noeud
```
