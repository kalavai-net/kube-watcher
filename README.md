# Kube-Watcher

Set of OpenFaaS functions to request Kubernetes API information in Kalavai.

Python kubernetes API reference https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md


## Install

Python must be < 3.12 (AttributeError: module 'ssl' has no attribute 'wrap_socket')

```bash
conda create --name kube-watcher python=3.9
conda activate kube-watcher
pip install -e .
```

## FastAPI service

Build docker image:
```bash
docker build -t kube_watcher .
docker tag kube_watcher:latest bundenth/kube_watcher:v1.1.1
docker push bundenth/kube_watcher:v1.1.1
```

### Configure endpoints

There are two endpoints that the API service uses and need to be configured as environment variables:
- `PROMETHEUS_ENDPOINT`: point to the prometheus instance where your cluster stats are dumped to. This usually is a service that listens to port 9090.
- `OPENCOST_ENDPOINT`: point to the opencost service instance that monitors cost and workload in your cluster. Usually a service that listens to port 9003

If you are doing a local deployment (on your local machine), you can specify both as environmental variables and run the local server with uvicorn:

```bash
IN_CLUSTER=False KW_USE_AUTH=False PROMETHEUS_ENDPOINT=http://10.43.164.196:9090 OPENCOST_ENDPOINT=http://10.43.53.194:9003 uvicorn kube_watcher.server:app
```

IN_CLUSTER=False PROMETHEUS_ENDPOINT=http://10.43.100.250:9090 OPENCOST_ENDPOINT=http://10.43.53.194:9003 uvicorn kube_watcher.server:app

Note that you must set `IN_CLUSTER` to False since you are not running inside a pod. This will make `kube-watcher` load the cluster configuration from your `~/.kube/config` file.

If you want to deploy to kubernetes, you'll have to set the environmental variables within the YAML deployment, then run:

```bash
kubectl apply -f kube_deployment.yaml
```

### Finding out the endpoints

To find out what endpoints to use, execute in your cluster:

kubectl get svc -A

Then from the list of services, choose the IPs for prometheus (listening to port 9090) and opencost (listening to port 9003). For example:

```bash
default           prometheus-kube-prometheus-prometheus                   ClusterIP      10.43.100.250   <none>                                    9090/TCP,8080/TCP
default           prometheus-kube-prometheus-alertmanager                 ClusterIP      10.43.229.137   <none>                                    9093/TCP,8080/TCP
kube-system       prometheus-kube-prometheus-kube-scheduler               ClusterIP      None            <none>                                    10259/TCP        
kube-system       prometheus-kube-prometheus-coredns                      ClusterIP      None            <none>                                    9153/TCP         
kube-system       prometheus-kube-prometheus-kube-controller-manager      ClusterIP      None            <none>                                    10257/TCP        
kube-system       prometheus-kube-prometheus-kube-etcd                    ClusterIP      None            <none>                                    2381/TCP         
kube-system       prometheus-kube-prometheus-kube-proxy                   ClusterIP      None            <none>                                    10249/TCP        
opencost          opencost                                                ClusterIP      10.43.140.3     <none>                                    9003/TCP,9090/TCP 
```

In this case, the we would choose the following:
- `PROMETHEUS_ENDPOINT`: 10.43.100.250:9090
- `OPENCOST_ENDPOINT`: 10.43.140.3


# DEPRECATED

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





### Check valid username/password

RESULT=$(curl -X GET http://localhost:8009/v1/validate_user -H 'Content-Type: application/json' -d '{"username":"EMAIL", "password":"PASSWORD"}')



## Langflow API

Get flows:

curl -X 'GET' \
  'https://carlosfm.playground.test.k8s.mvp.kalavai.net/api/v1/api_key/' \
  -H 'accept: application/json'\
  -H 'x-api-key: sk-v_y7ppXDC6xieH2N4Zpn_GaOAoyjDdQuKVzyYGv8YGw'
