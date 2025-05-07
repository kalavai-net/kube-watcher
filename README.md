# Kube-Watcher

API to handle kubernetes-specific functionality on behalf of the kalavai client. It includes template recipes for Kalavai jobs, designed to automate deployment of distributed workloads in Kalavai LLM pools.

Users should not need to install (or even care about) this library. It is deployed automatically as part of any LLM Pool. For installation and usage of LLM pools, visit our [kalavai client repository](https://github.com/kalavai-net/kalavai-client).


## Job templates

Template jobs built by Kalavai and the community make deploying distributed workflows easy for end users.

Templates are like recipes, where developers describe what worker nodes should run, and users customise the behaviour via pre-defined parameters. Kalavai handles the heavy lifting: workload distribution, communication between nodes and monitoring the state of the deployment to restart the job if required.

See [here](templates/README.md) for more details on how they work and to contribute.


## Development

### Install

Python must be < 3.12 (AttributeError: module 'ssl' has no attribute 'wrap_socket')

```bash
conda create --name kube-watcher python=3.9
conda activate kube-watcher
pip install -e .
```

Build docker image:
```bash
docker build -t kube-watcher .
docker tag kube-watcher:latest bundenth/kube-watcher:latest
docker push bundenth/kube-watcher:latest
```

### Configure endpoints

There are two endpoints that the API service uses and need to be configured as environment variables:
- `PROMETHEUS_ENDPOINT`: point to the prometheus instance where your cluster stats are dumped to. This usually is a service that listens to port 9090.
- `OPENCOST_ENDPOINT`: point to the opencost service instance that monitors cost and workload in your cluster. Usually a service that listens to port 9003

If you are doing a local deployment (on your local machine), you can specify both as environmental variables and run the local server with uvicorn:

```bash
IN_CLUSTER=False KW_USE_AUTH=False PROMETHEUS_ENDPOINT=http://10.43.164.196:9090 OPENCOST_ENDPOINT=http://10.43.53.194:9003 uvicorn kube_watcher.api:app
```

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


curl -X POST "http://localhost:8000/v1/add_labels_to_node" \
     -H "X-API-KEY: your-admin-key" \
     -H "Content-Type: application/json" \
     -d '{
           "node_name": "pop-os",
           "labels": {
             "environment": "production",
             "monitoring": "enabled"
           }
         }'