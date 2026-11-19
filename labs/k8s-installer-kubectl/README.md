# Install and configure kubectl

This course has you practise, on the lab machine, every move of the lesson:
pick a version, download a pinned binary, check its fingerprint, install it,
wire a completion and an alias, then reach the cluster. You work on **another
version** and under **another name** than the challenge does: the challenge is
left whole for the end.

Related page: [Install and configure kubectl](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/install-and-configure-kubectl/).

## 🔧 Before you start

```bash
dsoxlab run k8s-installer-kubectl
```

The command prepares the `k8s-kind.lab` machine and connects you to it. A kind
cluster named `lab` is already running, on Kubernetes `v1.37.0`, and your
`~/.kube/config` file points at it. kubectl itself has been removed: that is
what the lab is about. The outputs below were recorded on this machine
(Debian 13.7, amd64) on 19 November 2026.

## 📚 Exercise 1: pick a version within the allowed skew

The kubectl client may differ from the server by **one minor version at
most**. The cluster runs 1.37: a 1.36, 1.37 or 1.38 client talks to it. Look up
the current stable version, then the latest release of the 1.36 branch.

```bash
curl -fsSL https://dl.k8s.io/release/stable.txt
```

```text
v1.37.2
```

```bash
curl -fsSL https://dl.k8s.io/release/stable-1.36.txt
```

```text
v1.36.6
```

The server's answer does not end with a line break: your prompt shows right
after the version, that is expected.

The first version is the one the challenge will ask for. For the exercise,
take the second one, `v1.36.6`: one minor version below the cluster, so within
the allowed skew. The `stable-1.36.txt` file gives the latest patch of a given
branch, which is what you need when you must stay on one minor version.

## 📚 Exercise 2: download the binary and its fingerprint, pinned

Write the version once, then download the binary and the `.sha256` file
published next to it, in a scratch directory.

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

Both files necessarily come from the same version, since the `BASE` variable
names them both. Now make a typo in the version on purpose, to see what the
`-f` option does:

```bash
curl -fsSLO "https://dl.k8s.io/release/v1.36.66/bin/linux/amd64/kubectl"
```

```text
curl: (22) The requested URL returned error: 404
```

`curl` fails with code 22 instead of saving the error page under the name
`kubectl`. Without `-f`, you would get a `kubectl` file that is not a program.

## 📚 Exercise 3: check the fingerprint before installing

The `.sha256` file only holds the fingerprint: `echo` adds the file name that
`sha256sum --check` expects.

```bash
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
```

```text
kubectl: OK
```

Now see what an altered file gives. Copy the binary, add a single byte to it,
and check the copy against the same fingerprint:

```bash
cp kubectl kubectl-abime
printf x >> kubectl-abime
echo "$(cat kubectl.sha256)  kubectl-abime" | sha256sum --check
```

```text
kubectl-abime: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

One byte of difference is enough to change the fingerprint. On a `FAILED`, you
delete the file and download again: you never install a binary whose
fingerprint does not match.

## 📚 Exercise 4: install the binary without sudo, under another name

Install the checked copy in your home directory, under the name `kubectl136`,
then remove the scratch directory.

```bash
mkdir -p ~/.local/bin
install -m 0755 ~/essai-kubectl/kubectl ~/.local/bin/kubectl136
ls -l ~/.local/bin/kubectl136
cd ~ && rm -r ~/essai-kubectl
```

```text
-rwxr-xr-x 1 ansible ansible 59592866 Nov 19 09:21 /home/ansible/.local/bin/kubectl136
```

`install` copies the file and sets its permissions in a single command. Here
the binary belongs to you, since you installed it without `sudo`: your account
can modify it. The challenge asks for the opposite, a binary owned by `root`,
in `/usr/local/bin`.

Now ask the shell where it looks for programs:

```bash
echo "$PATH" | tr ":" "\n"
```

```text
/usr/local/bin
/usr/bin
/bin
/usr/games
```

`~/.local/bin` is not there: your session was opened before the directory
existed. Debian's `~/.profile` adds it at every login, provided it exists:

```bash
grep -n -A2 "local/bin" ~/.profile
```

```text
25:if [ -d "$HOME/.local/bin" ] ; then
26:    PATH="$HOME/.local/bin:$PATH"
27-fi
```

So replace your shell with a login shell, which reads `~/.profile` again, then
ask which file runs:

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

`command -v` gives the path of the program the shell finds. It is the first
thing to check when a command answers `command not found` or shows an
unexpected version.

## 📚 Exercise 5: see what the PATH does not find

Your client is called `kubectl136`. Ask the shell whether it knows `kubectl`:

```bash
command -v kubectl || echo "kubectl introuvable"
ls -l /usr/local/bin/
```

```text
kubectl introuvable
total 10288
-rwxr-xr-x 1 root root 10530942 Nov 19 09:19 kind
```

No program is named `kubectl`, and `/usr/local/bin` only holds `kind`.
Installing a binary somewhere else and under another name does not make it
available to everyone under its expected name: that is what the challenge will
ask you to do properly.

## 📚 Exercise 6: wire a completion and an alias, for this shell only

kubectl's bash completion relies on the `bash-completion` package. First check
whether it is there:

```bash
type _init_completion
```

```text
bash: type: _init_completion: not found
```

The package is not installed on this machine: without it, the Tab key does not
really complete subcommands. The challenge will ask you to install it. Here,
you only learn to **register** a completion and an alias, and to see what
becomes of them.

Load your client's completion script, create the alias `kc` and wire it to
kubectl's completion:

```bash
source <(kubectl136 completion bash)
alias kc=kubectl136
complete -o default -F __start_kubectl kc
complete -p kc
```

```text
complete -o default -F __start_kubectl kc
```

The alias `kc` is wired to kubectl's completion function. Now open a **new**
interactive shell and ask the same question:

```bash
bash -i -c 'complete -p kc; alias kc'
```

```text
bash: complete: kc: no completion specification
bash: alias: kc: not found
```

The new shell knows neither the completion nor the alias. What you type in a
shell disappears with it. For a completion or an alias to work in every new
terminal, it has to be written in `~/.bashrc`: that is what the challenge
checks, in a new shell.

## 📚 Exercise 7: reach the server and read the version skew

Run `version` without `--client`: kubectl also queries the server.

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

The `Server Version` line proves that kubectl reached the cluster API: client
on 1.36, server on 1.37, one minor version apart, so compatible.
`cluster-info` gives the API address. The port is picked at random when the
cluster is created, yours will differ.

## 🧹 Clean up

Remove what the exercises set up, then check that the machine is back to the
starting state of the challenge:

```bash
rm ~/.local/bin/kubectl136
rmdir ~/.local/bin
exit
dsoxlab check k8s-installer-kubectl
```

```text
╭── Result: k8s-installer-kubectl ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests  │
╰───────────────────────────────────╯
```

Zero out of six: nothing the exercises did counts for the challenge, and
nothing is left on the machine.

## 🎯 The challenge

Now do the challenge on your own: install kubectl `v1.37` for the whole system,
with its completion and the alias `k` in every new shell.

```bash
dsoxlab run k8s-installer-kubectl
dsoxlab challenge k8s-installer-kubectl
```
