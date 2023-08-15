# Kube-Watcher

Set of OpenFaaS functions to request Kubernetes API information in Kalavai.

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


# To connect to Graphana

In control plane:
```
kubectl port-forward deployment/prometheus-grafana 3000
```

Then forward the port 3000 to local machine (vscode)

Access graphana on localhost:3000
- admin
- prom-operator


# Connect to prometheus (via browser or API)

In control plane
```
kubectl port-forward --namespace default svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Then forward the port 9090 to local machine (vscode) 

Access prometheus UI on localhost:9090 or use python client to connect to port 9090


## TODO

Monitor resources --> active polling vs prometheus logging and querying in batch?
- Simpler to poll, but critical as it can miss data (if service goes down info is lost)
- More robust is to use prometheus (stores in database) as it can be done at any point, and if it fails, it is recoverable.


- [x] fetch resources available (allocatable) and registered (capacity)
- [x] fetch nodes readiness
- [x] deploy prometheus to store cluster metrics (can do nodes and resources?)
- [] access clusterIP of prometheus server from a cluster node (can't connect without port forwarding now)
- [] deploy database to store node readiness and user resource mappings
- [] service / application to register users (register resources to user accountns)
- [] service / application to monitor node readiness
- [] service / application to show resources availability
- [] service / application to manage user nodes (crud CPUs, memory, GPUs)