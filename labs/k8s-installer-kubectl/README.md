# Install and configure kubectl

kubectl is the command you use to talk to a Kubernetes cluster. In this
course, you redo the moves of the lesson one by one: pick a version, download
the program, check that it was not damaged, install it, give it a shortcut,
then check that it reaches the cluster.

To practise, you install **another version** of kubectl, under **another
name**. The challenge will ask you for the real installation: you will do it on
your own, at the end.

Related page: [Install and configure kubectl](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/install-and-configure-kubectl/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-installer-kubectl
```

You are now connected to the `k8s-kind.lab` machine. A cluster named `lab` is
already running there, on Kubernetes `v1.37.0`. Your `~/.kube/config` file
holds what it takes to connect to it. Only one thing is missing: kubectl,
which the lab removed.

The outputs shown in this course were recorded on this machine (Debian 13.7)
on 19 November 2026.

## 📚 Exercise 1: pick a kubectl version

Kubernetes versions are written as three numbers, for example `1.37.2`. The
second number, `37`, is called the **minor version**. kubectl and the cluster
may be one minor version apart, no more. The cluster runs 1.37: kubectl can
therefore be 1.36, 1.37 or 1.38.

Ask the Kubernetes site for the latest stable version:

```bash
curl -fsSL https://dl.k8s.io/release/stable.txt
```

```text
v1.37.2
```

Then for the latest version of the 1.36 branch:

```bash
curl -fsSL https://dl.k8s.io/release/stable-1.36.txt
```

```text
v1.36.6
```

The answer does not end with a line break. Your prompt therefore shows right
after the version: that is expected.

`v1.37.2` is the one the challenge will ask for. To practise, you take
`v1.36.6`: it is only one minor version away from the cluster, so it can talk
to it.

## 📚 Exercise 2: download kubectl and its fingerprint

kubectl is downloaded as a single file, ready to run: this is called a
**binary**. The site also publishes its **fingerprint** next to it: a string of
digits and letters computed from the content of the file. It is used to check
that the file was not damaged on the way.

Create a scratch directory and download both files. The version is written
only once, in a variable: you are sure the binary and the fingerprint come from
the same version.

```bash
mkdir ~/essai-kubectl && cd ~/essai-kubectl
KUBECTL_VERSION=v1.36.6
BASE="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64"
curl -fsSLO "${BASE}/kubectl"
curl -fsSLO "${BASE}/kubectl.sha256"
ls -l
```

```text
total 58204
-rw-rw-r-- 1 ansible ansible 59592866 Nov 19 09:21 kubectl
-rw-rw-r-- 1 ansible ansible       64 Nov 19 09:21 kubectl.sha256
```

You have the `kubectl` binary (about 57 MB) and its fingerprint,
`kubectl.sha256` (64 characters).

Now make a typo in the version on purpose, to see what happens:

```bash
curl -fsSLO "https://dl.k8s.io/release/v1.36.66/bin/linux/amd64/kubectl"
```

```text
curl: (22) The requested URL returned error: 404
```

Version `v1.36.66` does not exist, and `curl` stops on an error. The `-f`
option is what makes it stop. Without it, `curl` would have saved the error
page under the name `kubectl`, and you would have a fake kubectl.

## 📚 Exercise 3: check the fingerprint before installing

Compare the downloaded binary with the published fingerprint:

```bash
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
```

```text
kubectl: OK
```

`OK`: the file is indeed the one the project published.

Now see what happens with a damaged file. Copy the binary, add a single letter
at its end, and check the copy:

```bash
cp kubectl kubectl-abime
printf x >> kubectl-abime
echo "$(cat kubectl.sha256)  kubectl-abime" | sha256sum --check
```

```text
kubectl-abime: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

One extra letter is enough: the fingerprint no longer matches, and the check
shows `FAILED`. If this happens to you, do not install the file. Delete it and
download it again.

## 📚 Exercise 4: install kubectl in your home directory

Install the checked copy in `~/.local/bin`, under the name `kubectl136`.
`install` copies the file and makes it runnable in a single command. Then
delete the scratch directory.

```bash
mkdir -p ~/.local/bin
install -m 0755 ~/essai-kubectl/kubectl ~/.local/bin/kubectl136
ls -l ~/.local/bin/kubectl136
cd ~ && rm -r ~/essai-kubectl
```

```text
-rwxr-xr-x 1 ansible ansible 59592866 Nov 19 09:21 /home/ansible/.local/bin/kubectl136
```

The file belongs to your account (`ansible`), since you installed it without
`sudo`. The challenge will ask for the opposite: an installation for the whole
machine, in `/usr/local/bin`, with `sudo`.

When you type a command, the shell looks for it in a list of directories. This
list is called the **PATH**. Show it, one directory per line:

```bash
echo "$PATH" | tr ":" "\n"
```

```text
/usr/local/bin
/usr/bin
/bin
/usr/games
```

`~/.local/bin` is not in the list. The PATH was set when your session opened,
and at that time the directory did not exist yet. On Debian, the `~/.profile`
file adds it, if it exists:

```bash
grep -n -A2 "local/bin" ~/.profile
```

```text
25:if [ -d "$HOME/.local/bin" ] ; then
26:    PATH="$HOME/.local/bin:$PATH"
27-fi
```

This file is only read when a session opens. Open a new one with
`exec bash -l`, then ask where `kubectl136` is:

```bash
exec bash -l
command -v kubectl136
kubectl136 version --client
```

```text
/home/ansible/.local/bin/kubectl136
Client Version: v1.36.6
Kustomize Version: v5.8.1
```

`command -v` shows the path of the program the shell is going to run. Think of
it when a command answers `command not found`, or shows another version than
the one you expected.

## 📚 Exercise 5: check that `kubectl` is still not found

Your program is called `kubectl136`. Ask the shell whether it knows a
`kubectl` command:

```bash
command -v kubectl || echo "kubectl introuvable"
ls -l /usr/local/bin/
```

```text
kubectl introuvable
total 10288
-rwxr-xr-x 1 root root 10530942 Nov 19 09:19 kind
```

The shell finds no `kubectl` command, and `/usr/local/bin` only holds `kind`.
What you installed only serves you, under another name. The challenge will ask
you for a `kubectl` command everyone can use.

## 📚 Exercise 6: create a shortcut and a completion, then see them disappear

Two helpers make kubectl nicer to use:

- an **alias**, that is a shortcut: you type `kc`, the shell runs
  `kubectl136`;
- **completion**: you type the start of a command, the Tab key completes the
  rest.

On Debian, completion needs the `bash-completion` package. Check whether it is
installed:

```bash
type _init_completion
```

```text
bash: type: _init_completion: not found
```

It is not: the Tab key will not really complete commands. The challenge will
ask you to install it. Here, you only learn to create the alias and to declare
the completion.

Load kubectl's completion, create the `kc` alias, then tell the shell that
`kc` completes like kubectl:

```bash
source <(kubectl136 completion bash)
alias kc=kubectl136
complete -o default -F __start_kubectl kc
complete -p kc
```

```text
complete -o default -F __start_kubectl kc
```

The last line confirms that `kc` uses kubectl's completion. Now open a **new**
shell and ask the same question:

```bash
bash -i -c 'complete -p kc; alias kc'
```

```text
bash: complete: kc: no completion specification
bash: alias: kc: not found
```

The new shell knows neither the alias nor the completion. Everything you type
in a terminal is forgotten when it closes. To keep them, you must write them in
the `~/.bashrc` file, which bash reads every time it opens. That is what the
challenge will check, in a new shell.

## 📚 Exercise 7: check that kubectl reaches the cluster

Run `version` without `--client`: kubectl also asks the cluster for its
version.

```bash
kubectl136 version
kubectl136 cluster-info
```

```text
Client Version: v1.36.6
Kustomize Version: v5.8.1
Server Version: v1.37.0
Kubernetes control plane is running at https://127.0.0.1:39177
CoreDNS is running at https://127.0.0.1:39177/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

The `Server Version` line shows that kubectl did reach the cluster. You also
see the gap: kubectl on 1.36, cluster on 1.37, a single minor version apart.
`cluster-info` gives the address of the cluster. The port number changes every
time a cluster is created: yours will be different.

## 🧹 Clean up

First delete what you created during the exercises: the `kubectl136` program.

```bash
rm ~/.local/bin/kubectl136
rmdir ~/.local/bin
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-installer-kubectl
dsoxlab check k8s-installer-kubectl
```

```text
╭── Result: k8s-installer-kubectl ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests  │
╰───────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you, untouched.

## 🎯 The challenge

Your turn, on your own this time: install kubectl `v1.37` for the whole
machine, with the `k` alias and completion, which must work in every new
terminal.

```bash
dsoxlab run k8s-installer-kubectl
dsoxlab challenge k8s-installer-kubectl
```
