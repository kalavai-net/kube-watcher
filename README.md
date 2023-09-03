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


# Serverless Kubernetes API

OpenFaaS for serverless functions to help worker clients access kubernetes stats.

Example: https://medium.com/@turcios.kevinj/get-started-with-the-kubernetes-python-client-on-openfaas-d5a8eb2f3eca

Current functions

- get-node-stats --> for a node(s) get connectivity stats
- get-capacity --> for the network, get allocatable, capacity and online availability


## Install

```bash
curl -sSL https://cli.openfaas.com | sudo sh
curl -sLS https://get.arkade.dev | sudo sh
arkade install openfaas
```

Create a python function from template:
```bash
faas-cli new --lang python3 get-all-pods --prefix <YOUR_DOCKERHUB_USERNAME> --gateway http://127.0.0.1:31112
```

Template will be created in folder get-all-pods

Add dependencies to requirements.txt
```bash
kubernetes
```

Add to template/python3/template.yml:
```yaml
  - name: kubernetes-client
    packages:
      - g++
      - libffi-dev
      - openssl-dev
```

Apply read only role for namespace openfaas-fn
```bash
kubectl apply -f cluster_role.yaml
```

Login to openfaas
```bash
kubectl port-forward -n openfaas svc/gateway 8080:8080 &
PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)
echo -n $PASSWORD | faas-cli login --username admin --password-stdin
```

Login to private image registry:
```bash
faas-cli registry-login --username admin --password admin --server 159.65.30.72:32000
```

Build and deploy function:
```bash
faas-cli up --build-option kubernetes-client -f get-all-pods.yml
```

To test the function:

```
http://159.65.30.72:31112/ui/
http://159.65.30.72:31112/function/get-all-pods
```

### Install notes

```bash
=======================================================================
= OpenFaaS has been installed.                                        =
=======================================================================

# Get the faas-cli
curl -SLsf https://cli.openfaas.com | sudo sh

# Forward the gateway to your machine
kubectl rollout status -n openfaas deploy/gateway
kubectl port-forward -n openfaas svc/gateway 8080:8080 &

# If basic auth is enabled, you can now log into your gateway:
PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)
echo -n $PASSWORD | faas-cli login --username admin --password-stdin

faas-cli store deploy figlet
faas-cli list

# For Raspberry Pi
faas-cli store list \
 --platform armhf

faas-cli store deploy figlet \
 --platform armhf
```


## FastAPI service

Build docker image:
```bash
docker build -t kube_watcher .
docker tag kube_watcher:latest bundenth/kube_watcher:v9
docker push bundenth/kube_watcher:v9
```

Create service and deployment

```bash
kubectl apply -f kube_deployment.yaml
```


### Check valid username/password

RESULT=$(curl -X GET http://localhost:8009/v1/validate_user -H 'Content-Type: application/json' -d '{"username":"EMAIL", "password":"PASSWORD"}')
