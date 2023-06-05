# Kube-Watcher

Python kubernetes API reference https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md


## Install

```bash
virtualenv -p python3 env
source env/bin/activate
pip install -e .
```

## Create bearer tokens

Same tokens a for Kubernetes-dashboard work.

In the kube-control-plane, execute (you can configure the name of the service account in the script changing the variable ACCOUNT_NAME):

```bash
sh generate_token.sh
```


The easiest way is to load the cluster config file loaded in the service. The config file is usually found on the control-plane node under `~/.kube/config`.

```python
kubernetes.config.load_kube_config("cluster_config.yaml")
```

Make sure to update the server field to point at the control-plane node.

```yaml
...
clusters:
- cluster:
    server: https://<control-plane-ip>:6443
...
```

## Python lib to create pods

https://www.phillipsj.net/posts/k8s-yaml-alternative-python/


## Deployment to kubernetes

https://github.com/janakiramm/kubernetes-101
https://dev.to/itminds/hello-python-through-docker-and-kubernetes-379d
https://developer.ibm.com/tutorials/scalable-python-app-with-kubernetes/