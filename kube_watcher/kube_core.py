import json
import time
import base64
import yaml
from collections import defaultdict

from kubernetes import config, client, utils

from kube_watcher.utils import (
    create_flow_deployment_yaml,
    create_agent_builder_deployment_yaml,
    cast_resource_value,
    parse_resource_value
)


class KubeAPI():
    def __init__(self, in_cluster=False):
        if in_cluster:
            config.load_incluster_config()
        else:
            # Only works if this script is run by K8s as a POD
            config.load_kube_config()
        self.core_api = client.CoreV1Api()

    def _extract_resources(self, fn):
        """Generalisation to extract values in dict form"""
        nodes = self.core_api.list_node()
        data = {"online": defaultdict(int), "total": defaultdict(int)}
        for node in nodes.items:
            status = True if self.extract_node_readiness(node).status == "True" else False
            if status:
                data["online"]["n_nodes"] += 1
                parse_resource_value(resources=fn(node), out_data_dict=data["online"])
            data["total"]["n_nodes"] += 1
            parse_resource_value(resources=fn(node), out_data_dict=data["total"])
        return data
    
    
    def extract_node_readiness(self, node):
        """Extract the readiness of a node from its status information (from extract_node_status)"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition
        return None
    
    def extract_cluster_labels(self):
        """Similar to extract_cluster_capacity but with node labels.
        - total --> nodes labels as reported in node labels
        - online --> nodes labels (for those with status Ready) as reported in node labels
        """
        fn = lambda node: node.metadata.labels
        return self._extract_resources(fn=fn)
    
    def extract_node_conditions(self, node, conditions=None):
        """Extract the readiness of a node from its status information (from extract_node_status)"""
        all_conditions = {}
        for c in node.status.conditions:
            if conditions is not None:
                if c.type not in conditions:
                    continue
            all_conditions[c.type] = c.status == "True"
        return all_conditions
    
    def get_nodes_states(self, conditions=None):
        """Get the status of nodes on certain conditions (default all)"""
        nodes = self.core_api.list_node()
        node_status = {}
        for node in nodes.items:
            node_status[node.metadata.name] = self.extract_node_conditions(node=node, conditions=conditions)
        
        return node_status
    
    def get_nodes_with_pressure(self, pressures=["DiskPressure", "MemoryPressure", "PIDPressure"]):
        """Get nodes with pressure signals"""
        nodes = self.core_api.list_node()
        all_pressures = {}
        for node in nodes.items:
            pressures = { key: value for key, value in self.extract_node_conditions(node=node, conditions=pressures).items() if value }
            if pressures:
                all_pressures[node.metadata.name] = pressures
        return all_pressures
    
    def get_pods_with_status(self, node_name, statuses=["Failed", "Unknown"]): # Failed, Running, Succeeded, Pending, Unknown
        """Get pods with failing statuses (or any other specific status)"""
        pods = self.core_api.list_pod_for_all_namespaces(watch=False)
        pods_on_node = [pod for pod in pods.items if pod.spec.node_name == node_name]
        all_pods = {}
        for pod in pods_on_node:
            if pod.status.phase in statuses:
                all_pods[pod.metadata.name] = pod.status.phase
        return all_pods
    
    def get_unschedulable_pods(self):
        """Get pods that cannot be scheduled due to lack of resources"""
        pods = self.core_api.list_pod_for_all_namespaces(watch=False)
        # Filter for pending pods due to insufficient resources
        pending_pods = []
        for pod in pods.items:
            if pod.status.phase == 'Pending':
                for condition in pod.status.conditions or []:
                    if condition.reason == 'Unschedulable':
                        if 'Insufficient' in condition.message:
                            pending_pods.append(pod)
                            break
        # Print the pending pods
        unschedulable = {}
        for pod in pending_pods:
            unschedulable[pod.metadata.name] = {
                "namespace": pod.metadata.namespace,
                "reason": pod.status.conditions[-1].message
            }
        return unschedulable
    
    def get_total_allocatable_resources(self):
        """Get total allocatable resources (available and used) in the cluster"""
        
        total_resources = self._extract_resources(fn=lambda node: node.status.allocatable)
        return total_resources["total"]
    
    def get_available_resources(self):
        """Gets available resources (not currently used) in the cluster:
        - cpu
        - memory
        - gpus
        - pods
        """
        total_resources = self._extract_resources(fn=lambda node: node.status.allocatable)
        available_resources = total_resources["online"]

        # remove requested (and used) resources
        pods = self.core_api.list_pod_for_all_namespaces(watch=False).items
        for pod in pods:
            node_name = pod.spec.node_name
            if node_name and pod.status.phase == 'Running':
                available_resources["pods"] -= 1
                for container in pod.spec.containers:
                    requests = container.resources.requests
                    if requests:
                        for resource in available_resources.keys():
                            if resource in requests:
                                available_resources[resource] -= cast_resource_value(requests[resource])

        return available_resources

    def get_node_labels(self, node_names=None):
        nodes = self.core_api.list_node()
        node_labels = {}
        for node in nodes.items:
            name = node.metadata.name
            if node_names is not None and name not in node_names:
                pass
            else:
                node_labels[name] = node.metadata.labels
        return node_labels

    def kube_deploy(self, yaml_strs):
        yamls = yaml_strs.split("---")
        result = True
        for yaml_str in yamls:
            print("DEPLOYING YAML")
            yaml_obj =  yaml.safe_load(yaml_str)
            print(yaml_obj)
            # load kubernetes client
            k8s_client = client.api_client.ApiClient()
            # create pods from yaml object
            try:
                res = utils.create_from_yaml(
                    k8s_client,
                    yaml_objects=[yaml_obj],
                )
                print(res)
            except Exception as e:
                result = False
                print(str(e))
        return result
    

    def kube_deploy_plus(self, yaml_strs):
        yamls = yaml_strs.split("---")
        deployment_results = {
            "successful": [],
            "failed": []
        }

        for yaml_str in yamls:
            if yaml_str.strip():  # Check if the yaml_str is not just whitespace
                yaml_obj = yaml.safe_load(yaml_str)
                k8s_client = client.api_client.ApiClient()

                try:
                    res = utils.create_from_yaml(
                        k8s_client,
                        yaml_objects=[yaml_obj],
                    )
                    # Assuming res contains some identifiable information about the resource
                    deployment_results["successful"].append(str(res))
                except Exception as e:
                    # Append the yaml that failed and the exception message for clarity
                    deployment_results["failed"].append({"yaml": yaml_str, "error": str(e)})

        return deployment_results
    
    def kube_deploy_custom_object(self, group, api_version, namespace, plural, body):
        deployment_results = {
            "successful": [],
            "failed": []
        }
        api = client.CustomObjectsApi(client.api_client.ApiClient())
        if body.strip():
            yaml_obj = yaml.safe_load(body)
            try:
                res = api.create_namespaced_custom_object(
                    group,
                    api_version,
                    namespace,
                    plural,
                    yaml_obj
                )
                # Assuming res contains some identifiable information about the resource
                deployment_results["successful"].append(str(res))
            except Exception as e:
                # Append the yaml that failed and the exception message for clarity
                deployment_results["failed"].append({"yaml": body, "error": str(e)})

        return deployment_results
    
    def deploy_flow(
        self,
        deployment_name,
        namespace,
        flow_id,
        flow_url,
        api_key,
        num_cores=1,
        ram_memory="1Gi"
    ):
        # Deploy a deepsparse model
        yaml = create_flow_deployment_yaml(
            values={
                "deployment_name": deployment_name,
                "username": namespace,
                "num_cores": num_cores,
                "ram_memory": ram_memory,
                "api_key": api_key,
                "flow_id": flow_id,
                "flow_url": flow_url
            }
        )
        return self.kube_deploy(yaml)
    
    def delete_flow(
        self,
        deployment_name,
        namespace
    ):
        """Delete a flow deployment within a namespace.
        """
        try:
            # TODO create a CRD for flow deployments so we don't have to delete individual components
            # service
            self.core_api.delete_namespaced_service(name=f"{deployment_name}-service", namespace=namespace)
            # deployment
            client.AppsV1Api().delete_namespaced_deployment(name=f"{deployment_name}", namespace=namespace)
            # ingress
            client.NetworkingV1Api().delete_namespaced_ingress(name=f"{deployment_name}-ingress", namespace=namespace)
            return True
        except Exception as e:
            print(f"Exception when calling CoreV1Api->delete_namespace: {str(e)}")

    def list_deployments(self, namespace, inspect_services=False):
        """ List deployments in a namespace"""
        k8s_apps = client.AppsV1Api()
        deployments = k8s_apps.list_namespaced_deployment(namespace)
        model_deployments = defaultdict(dict)
        for deployment in deployments.items:
            model_deployments[deployment.metadata.name] = {
                "replicas": deployment.spec.replicas,
                "available_replicas": deployment.status.available_replicas,
                "unavailable_replicas": deployment.status.unavailable_replicas,
                "ready_replicas": deployment.status.ready_replicas,
                "paused": deployment.spec.paused
            }
        
        if inspect_services:
            services = self.core_api.list_namespaced_service(namespace)
            for service in services.items:
                model_deployments[service.metadata.name]["cluster_ip"] = service.spec.cluster_ip
                model_deployments[service.metadata.name]["ports"] = [(port.node_port, port.target_port) for port in service.spec.ports]

        return model_deployments
    
    
    def deploy_agent_builder(
        self,
        deployment_name,
        namespace,
        username,
        password,
        num_cores=1,
        ram_memory="1Gi",
        storage_memory="0.5Gi",
        replicas=1
    ):
        # Deploy a deepsparse model
        yaml = create_agent_builder_deployment_yaml(
            values={
                "deployment_name": deployment_name,
                "namespace": namespace,
                "username": base64.b64encode(username.encode("ascii")).decode("ascii"),
                "password": password,
                "num_cores": num_cores,
                "ram_memory": ram_memory,
                "storage_memory": storage_memory,
                "replicas": replicas
            }
        )
        return self.kube_deploy(yaml)
    
    def delete_agent_builder(
        self,
        deployment_name,
        namespace
    ):
        """Delete an agent builder deployment within a namespace.
        """
        try:
            # TODO create a CRD for flow deployments so we don't have to delete individual components
            # service
            self.core_api.delete_namespaced_service(name=f"{deployment_name}-agent-builder-service", namespace=namespace)
            # deployment
            client.AppsV1Api().delete_namespaced_deployment(name=f"{deployment_name}-agent-builder", namespace=namespace)
            # ingress
            client.NetworkingV1Api().delete_namespaced_ingress(name=f"{deployment_name}-agent-builder-ingress", namespace=namespace)
            # pvc
            self.core_api.delete_namespaced_persistent_volume_claim(name=f"{deployment_name}-agent-builder-pvc", namespace=namespace)
            return True
        except Exception as e:
            print(f"Exception when calling delete agent builder: {str(e)}")
    
    ## DEPRECATED ##
        
    def deploy_generic_model(self, config: str):
        # Deploy a generic config
        return self.kube_deploy_plus(config)

    def delete_labeled_resources(self, namespace, label_key: str, label_value: str = None):
        """Delete all resources in a namespace with a given label"""

        core_api = client.CoreV1Api()
        apps_api = client.AppsV1Api()
        batch_v1_api = client.BatchV1Api()

        deleted_resources = []
        failed_resources = []

        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        resource_types = {
            'pod': (core_api.list_namespaced_pod, core_api.delete_namespaced_pod),
            'service': (core_api.list_namespaced_service, core_api.delete_namespaced_service),
            'daemonset': (apps_api.list_namespaced_daemon_set, apps_api.delete_namespaced_daemon_set),
            'deployment': (apps_api.list_namespaced_deployment, apps_api.delete_namespaced_deployment),
            'replicaset': (apps_api.list_namespaced_replica_set, apps_api.delete_namespaced_replica_set),
            'statefulset': (apps_api.list_namespaced_stateful_set, apps_api.delete_namespaced_stateful_set),
            'job': (batch_v1_api.list_namespaced_job, batch_v1_api.delete_namespaced_job),
            'persistentvolumeclaim': (core_api.list_namespaced_persistent_volume_claim, core_api.delete_namespaced_persistent_volume_claim)
 
        }

        for resource_type, (list_func, delete_func) in resource_types.items():
            try:
                resources = list_func(namespace, label_selector=label_selector)
                for resource in resources.items:
                    try:
                        delete_func(name=resource.metadata.name, namespace=namespace)
                        deleted_resources.append(f"{resource_type}/{resource.metadata.name}")
                    except Exception as e:
                        failed_resources.append(f"{resource_type}/{resource.metadata.name}: {str(e)}")
            except Exception as e:
                print(f"Exception when listing {resource_type}: {e}")

        return {
            "deleted_resources": deleted_resources,
            "failures": failed_resources
        }

    def find_resources_with_label(self, namespace:str, label_key:str, label_value=None):
        core_api = client.CoreV1Api()
        apps_api = client.AppsV1Api()
        batch_v1_api = client.BatchV1Api()
        #batch_v1beta1_api = client.BatchV1beta1Api()

        resources_found = {}

        resource_types = {
            'pod': core_api.list_namespaced_pod,
            'service': core_api.list_namespaced_service,
            'daemonset': apps_api.list_namespaced_daemon_set,
            'deployment': apps_api.list_namespaced_deployment,
            'replicaset': apps_api.list_namespaced_replica_set,
            'statefulset': apps_api.list_namespaced_stateful_set,
            'job': batch_v1_api.list_namespaced_job,
            'persistentvolumeclaim': core_api.list_namespaced_persistent_volume_claim
        }

        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        for resource_type, list_func in resource_types.items():
            try:
                resources = list_func(namespace, label_selector=label_selector)
                if resources.items:
                    resources_found[resource_type] = {resource.metadata.name: resource.metadata.to_dict() for resource in resources.items}
            except Exception as e:
                print(f"Exception when checking for {resource_type}: {e}")

        return resources_found

    def find_resources_with_label(self, namespace:str, label_key:str, label_value=None):
        # TODO: Update to give Cluster IP
        
        core_api = client.CoreV1Api()
        apps_api = client.AppsV1Api()
        batch_v1_api = client.BatchV1Api()
        #batch_v1beta1_api = client.BatchV1beta1Api()

        resources_found = []

        resource_types = {
            'pod': core_api.list_namespaced_pod,
            'service': core_api.list_namespaced_service,
            'daemonset': apps_api.list_namespaced_daemon_set,
            'deployment': apps_api.list_namespaced_deployment,
            'replicaset': apps_api.list_namespaced_replica_set,
            'statefulset': apps_api.list_namespaced_stateful_set,
            'job': batch_v1_api.list_namespaced_job,
            'persistentvolumeclaim': core_api.list_namespaced_persistent_volume_claim
        }

        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        for resource_type, list_func in resource_types.items():
            try:
                resources = list_func(namespace, label_selector=label_selector)
                if resources.items:
                    #resources_found[resource_type] = {resource.metadata.name: resource.metadata.to_dict() for resource in resources.items}
                    for resource in resources.items:
                        node_ports = []
                        if resource.spec.type == "NodePort":
                            for port in resource.spec.ports:
                                # Check if the port is a NodePort and add it to the list
                                if port.node_port:
                                    node_ports.append(port.node_port)

                        

                        resource = {
                            "type": resource_type,
                            "namespace": namespace,
                            "name": resource.metadata.name,
                            "labels": resource.metadata.labels,
                            "metadata": resource.metadata.to_dict(),
                            "spec": resource.spec.to_dict(),
                            "node_ports": node_ports,
                            "label_key": label_key,
                            "label_value": resource.metadata.labels.get(label_key, None)
                        }
                        resources_found.append(resource)

            except Exception as e:
                print(f"Exception when checking for {resource_type}: {e}")

        return resources_found

    def find_nodeport_url(self, namespace:str, label_key:str, label_value=None):
        """ Termporary Way to find the nodeport url for a service with a given label"""

        core_api = client.CoreV1Api()
    
        # pull only the service with the given label
        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        service_ports = {}        

        resources = core_api.list_namespaced_service(namespace, label_selector=label_selector)
        if resources.items:
            for service in resources.items:
                node_ports = []
                if service.spec.type == "NodePort":
                    for port in service.spec.ports:
                        # Check if the port is a NodePort and add it to the list
                        if port.node_port:
                            node_ports.append(port.node_port)
                service_ports[service.metadata.name] = max(node_ports)

        return service_ports



if __name__ == "__main__":
    
    api = KubeAPI(in_cluster=False)

    res = api.kube_deploy_custom_object(
        group="leaderworkerset.x-k8s.io",
        api_version="v1",
        namespace="default",
        plural="leaderworkersets",
        body="""
apiVersion: leaderworkerset.x-k8s.io/v1
kind: LeaderWorkerSet
metadata:
  name: leaderworkerset-sample
spec:
  replicas: 3
  leaderWorkerTemplate:
    size: 4
    workerTemplate:
      spec:
        containers:
        - name: nginx
          image: nginx:1.14.2
          resources:
            limits:
              cpu: "100m"
            requests:
              cpu: "50m"
          ports:
          - containerPort: 8080"""
    )
    print(res)
    exit()
    
    username = "carlosfm2"
    password = "password"
    deployment_name = "my-agent-1"
    flow_id = "8fa8c401-7c10-417b-bd19-e84ea6236a4f"
    flow_url = "https://carlosfm.playground.test.k8s.mvp.kalavai.net/api/v1/process"
    api_key = "sk-Qn4Ns14yHy1UUacq9cwfe6k9jeDyvE9zVepTENeQAaw"
    
    api.deploy_agent_builder(
        deployment_name="builder",
        namespace="carlosfm",
        username="carlosfm",
        password=base64.b64encode(password.encode("ascii")).decode("ascii")
    )
    
    # api.deploy_flow(
    #     deployment_name=deployment_name,
    #     namespace=username,
    #     flow_id=flow_id,
    #     flow_url=flow_url,
    #     api_key=api_key
    # )
    # api.delete_flow(
    #     deployment_name=deployment_name,
    #     namespace=username
    # )
