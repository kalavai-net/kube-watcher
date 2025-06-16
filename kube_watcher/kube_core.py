import json
import time
import os
import requests
import base64
import yaml
from collections import defaultdict

from kubernetes import config, client, utils

from kube_watcher.utils import (
    create_flow_deployment_yaml,
    create_agent_builder_deployment_yaml,
    cast_resource_value,
    parse_resource_value,
    force_serialisation,
    extract_longhorn_metric_from_prometheus
)


LONGHORN_MANAGER_ENDPOINT = os.getenv("LONGHORN_MANAGER_ENDPOINT", "http://localhost:30132")


class KubeAPI():
    def __init__(self, in_cluster=False):
        if in_cluster:
            config.load_incluster_config()
        else:
            # Only works if this script is run by K8s as a POD
            config.load_kube_config()
        self.core_api = client.CoreV1Api()

    def _extract_resources(self, fn, node_names=None):
        """Generalisation to extract values in dict form"""
        nodes = self.core_api.list_node()
        data = {"online": defaultdict(int), "total": defaultdict(int)}
        for node in nodes.items:
            if node_names is not None and node.metadata.name not in node_names:
                continue
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
            # add schedulable state
            node_status[node.metadata.name]["unschedulable"] = False if node.spec.unschedulable is None else node.spec.unschedulable
        
        return node_status
    
    def get_nodes(self):
        node_list = self.core_api.list_node()
        nodes = []
        for spec in node_list.items:
            nodes.append(spec.metadata.name)
        return nodes
    
    def get_nodes_with_labels(self, labels: dict) -> list:
        """
        Get list of nodes that contain one or more specified labels (or annotations)
        
        Args:
            labels (dict): Dictionary of label key-value pairs to match
            
        Returns:
            list: List of node names that match the specified labels
        """
        nodes = self.core_api.list_node()
        matching_nodes = []
        
        for node in nodes.items:
            # Check labels
            node_labels = node.metadata.labels
            # Check annotations
            node_annotations = node.metadata.annotations
            # Check if all specified labels match either in labels or annotations
            if all(
                (node_labels and node_labels.get(key) == value) or 
                (node_annotations and node_annotations.get(key) == value) 
                for key, value in labels.items()
            ):
                matching_nodes.append(node.metadata.name)
                
        return matching_nodes
    
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
    
    def get_total_allocatable_resources(self, node_names=None):
        """Get total allocatable resources (available and used) in the cluster"""
        
        total_resources = self._extract_resources(
            fn=lambda node: node.status.allocatable,
            node_names=node_names)
        return total_resources["total"]
    
    def get_available_resources(self, node_names=None):
        """Gets available resources (not currently used) in the cluster:
        - cpu
        - memory
        - gpus
        - pods
        """
        total_resources = self._extract_resources(fn=lambda node: node.status.allocatable, node_names=node_names)
        available_resources = total_resources["online"]

        # remove requested (and used) resources
        pods = self.core_api.list_pod_for_all_namespaces(watch=False).items
        for pod in pods:
            node_name = pod.spec.node_name
            if node_names is not None and node_name not in node_names:
                continue
            if node_name and pod.status.phase == 'Running':
                available_resources["pods"] -= 1
                for container in pod.spec.containers:
                    reqs = container.resources.requests
                    if reqs:
                        for resource in available_resources.keys():
                            if resource in reqs:
                                available_resources[resource] -= cast_resource_value(reqs[resource])

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
    
    def get_node_annotations(self, node_names=None):
        nodes = self.core_api.list_node()
        node_labels = {}
        for node in nodes.items:
            name = node.metadata.name
            if node_names is not None and name not in node_names:
                pass
            else:
                node_labels[name] = node.metadata.annotations
        return node_labels
    
    def get_node_gpus(self, node_names=None, gpu_key="hami.io/node-nvidia-register"):

        nodes = self.core_api.list_node().items

        gpu_info = {}
        for node in nodes:
            if node_names is not None and node.metadata.name not in node_names:
                continue
            resources = self.get_available_resources(node_names=[node.metadata.name])
            gpu_capacity = node.status.capacity.get("nvidia.com/gpu", "0")

            gpu_info[node.metadata.name] = {
                "available": resources["nvidia.com/gpu"],
                "capacity": gpu_capacity,
                "gpus": []
            }
            # extract model information
            annotations = self.get_node_annotations(node_names=[node.metadata.name])
            node_states = self.get_nodes_states()
            for node, node_annotations in annotations.items():
                if gpu_key not in node_annotations:
                    continue
                gpus = node_annotations[gpu_key].split(":")
                for gpu_data in gpus:
                    data = gpu_data.split(",")
                    if len(data) < 6:
                        continue
                    gpu_info[node]["gpus"].append({
                        "ready": node_states[node]["Ready"],
                        "memory": data[2],
                        "model": data[4]
                    })
        return gpu_info
    
    def read_node(self, node_names: list=None):
        nodes = self.get_nodes()
        nodes_info = {}
        for node in nodes:
            if node_names is not None and node not in node_names:
                continue
            nodes_info[node] = self.core_api.read_node(node)
        
        return force_serialisation(nodes_info)

    def get_nodes_resources(self, node_names: list=None):
        nodes_info = self.read_node(node_names=node_names)
        nodes_resources = {}
        for node_name, node_spec in nodes_info.items():
            nodes_resources[node_name] = {
                key: cast_resource_value(value) for key, value in node_spec["status"]["allocatable"].items()
            }
        return force_serialisation(nodes_resources)
    
    def delete_node(self, node_name):
        return self.core_api.delete_node(node_name)
    
    def set_node_schedulable(self, node_name, state):
        # first drain the node
        if not state:
            pods = self.core_api.list_pod_for_all_namespaces(watch=False)
            for pod in pods.items:
                if pod.spec.node_name != node_name:
                    continue
                print(f"******* Evicting pod {pod.metadata.name} ({pod.metadata.namespace})")
                body = client.V1Eviction(
                    metadata=client.V1ObjectMeta(
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace
                    ),
                    delete_options=client.V1DeleteOptions()
                )
                self.core_api.create_namespaced_pod_eviction(
                    pod.metadata.name,
                    pod.metadata.namespace,
                    body
                )

        # then set unschedulable
        body = {
            "spec": {
                "unschedulable": not state
            }
        }
        return self.core_api.patch_node(node_name, body)

    def add_annotation_to_node(self, node_labels: dict, annotation: dict):
        """
        Add annotations to nodes that match the specified labels.
        
        Args:
            node_labels (dict): Dictionary of label key-value pairs to match
            annotation (dict): Dictionary of annotations to add to matching nodes
            
        Returns:
            list: List of node names that were updated
        """
        nodes = self.core_api.list_node()
        updated_nodes = []
        
        for node in nodes.items:
            # Check if all specified labels match
            if all(node.metadata.labels.get(key) == value for key, value in node_labels.items()):
                # Create a patch body with the new annotations
                patch_body = {
                    "metadata": {
                        "annotations": annotation
                    }
                }
                try:
                    # Patch the node with the new annotations
                    self.core_api.patch_node(node.metadata.name, patch_body)
                    updated_nodes.append(node.metadata.name)
                except Exception as e:
                    print(f"Failed to update node {node.metadata.name}: {str(e)}")
                    
        return updated_nodes

    def add_labels_to_node(self, node_name: str, new_labels: dict):
        """
        Add labels to a specific node by its name.
        
        Args:
            node_name (str): Name of the node to update
            new_labels (dict): Dictionary of labels to add to the node
            
        Returns:
            bool: True if the node was successfully updated, False otherwise
        """
        try:
            # Create a patch body with the new labels
            patch_body = {
                "metadata": {
                    "labels": new_labels
                }
            }
            # Patch the node with the new labels
            self.core_api.patch_node(node_name, patch_body)
            return True
        except Exception as e:
            print(f"Failed to update node {node_name}: {str(e)}")
            return False

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
    

    def kube_deploy_plus(self, yaml_strs, force_namespace=None):
        yamls = yaml_strs.split("---")
        deployment_results = defaultdict(list)
        custom_api = client.CustomObjectsApi(client.api_client.ApiClient())
        k8s_client = client.api_client.ApiClient()
        for yaml_str in yamls:
            if yaml_str.strip():  # Check if the yaml_str is not just whitespace
                yaml_obj = yaml.safe_load(yaml_str)
                try:
                    # Attempt custom deployment
                    group = yaml_obj["apiVersion"][:yaml_obj["apiVersion"].index("/")]
                    api_version = yaml_obj["apiVersion"][yaml_obj["apiVersion"].index("/")+1:]
                    if force_namespace is not None:
                        namespace = force_namespace
                    else:
                        if "metadata" in yaml_obj and "namespace" in yaml_obj["metadata"]:
                            namespace = yaml_obj["metadata"]["namespace"]
                        else:
                            namespace = "default"
                    plural = yaml_obj["kind"].lower() + "s"
                    res = custom_api.create_namespaced_custom_object(
                        group,
                        api_version,
                        namespace,
                        plural,
                        yaml_obj)
                    deployment_results["successful"].append(str(res))
                except Exception as e:
                    print(f"Failed automated deployment, trying default deployment. [{str(e)}")
                    try:
                        namespace = force_namespace if force_namespace is not None else "default"
                        res = utils.create_from_yaml(
                            k8s_client,
                            yaml_objects=[yaml_obj],
                            namespace=namespace
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
    
    def kube_get_custom_objects(self, group, api_version, namespace, plural, label_selector=None):

        objects =  client.CustomObjectsApi().list_namespaced_custom_object(
            group,
            api_version,
            namespace,
            plural,
            label_selector=label_selector)
        
        return objects
    
    def kube_get_status_custom_object(self, name, group, api_version, namespace, plural):
        try:
            api = client.CustomObjectsApi(client.api_client.ApiClient())
            res = api.get_namespaced_custom_object_status(
                group,
                api_version,
                namespace,
                plural,
                name
            )
            return res["status"]["conditions"]
        except:
            return None

    def kube_delete_custom_object(self, name, group, api_version, plural, namespace):
        api = client.CustomObjectsApi(client.api_client.ApiClient())
        res = api.delete_namespaced_custom_object(
            group,
            api_version,
            namespace,
            plural,
            name
        )
        return res
    
    def get_logs_for_pod(self, pod, namespace):
        response = self.core_api.read_namespaced_pod_log(
            name=pod,
            namespace=namespace
        )
        return response

    def describe_pod(self, pod, namespace):
        response = self.core_api.read_namespaced_pod(
            name=pod,
            namespace=namespace
        )
        return force_serialisation(response)
    
    def find_pods_with_label(self, namespace:str, label_key:str, label_value=None):

        resources_found = {}
        resource_types = {
            'pod': self.core_api.list_namespaced_pod
        }
        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        for resource_type, list_func in resource_types.items():
            try:
                resources = list_func(namespace, label_selector=label_selector)
                if resources.items:
                    for resource in resources.items:
                        resources_found[resource.metadata.name] = resource.to_dict()
            except Exception as e:
                print(f"Exception when checking for {resource_type}: {e}")

        return force_serialisation(resources_found)
    
    def get_specs_for_pod(self, pod_name, namespace):
        return self.core_api.read_namespaced_pod(
            name=pod_name,
            namespace=namespace
        )
    
    def get_logs_for_labels(self, label_key, label_value, namespace):
        """Get logs for all pods that match a label key:value"""
        pods = self.find_pods_with_label(
            namespace=namespace,
            label_key=label_key,
            label_value=label_value
        )
        logs = {}
        for pod_name in pods.keys():
            logs[pod_name] = {
                "logs": self.get_logs_for_pod(pod=pod_name, namespace=namespace),
                "pod": force_serialisation(self.get_specs_for_pod(pod_name=pod_name, namespace=namespace))
            }
        
        return logs
    
    def describe_pods_for_labels(self, label_key, label_value, namespace):
        """Get describe for all pods that match a label key:value"""
        pods = self.find_pods_with_label(
            namespace=namespace,
            label_key=label_key,
            label_value=label_value
        )
        logs = {}
        for pod_name in pods.keys():
            logs[pod_name] = self.describe_pod(pod=pod_name, namespace=namespace)
        
        return logs
    
    def list_namespaces(self):
        namespaces = self.core_api.list_namespace()
        return [ns["metadata"]["name"] for ns in force_serialisation(namespaces.items)]
    
    def list_namespaced_lws(self, namespace, label_selector):
        resources = self.kube_get_custom_objects(
            group="leaderworkerset.x-k8s.io",
            api_version="v1",
            plural="leaderworkersets",
            namespace=namespace,
            label_selector=label_selector
        )
        return resources

    def delete_namespaced_lws(self, name, namespace):
        return self.kube_delete_custom_object(
            group="leaderworkerset.x-k8s.io",
            api_version="v1",
            plural="leaderworkersets",
            name=name,
            namespace=namespace
        )
    
    def list_namespaced_vcjob(self, namespace, label_selector):
        resources = self.kube_get_custom_objects(
            group="batch.volcano.sh",
            api_version="v1alpha1",
            plural="jobs",
            namespace=namespace,
            label_selector=label_selector
        )
        return resources

    def delete_namespaced_vcjob(self, name, namespace):
        return self.kube_delete_custom_object(
            group="batch.volcano.sh",
            api_version="v1alpha1",
            plural="jobs",
            name=name,
            namespace=namespace
        )
    
    def list_namespaced_raycluster(self, namespace, label_selector):
        resources = self.kube_get_custom_objects(
            group="ray.io",
            api_version="v1",
            plural="rayclusters",
            namespace=namespace,
            label_selector=label_selector
        )
        return resources

    def delete_namespaced_raycluster(self, name, namespace):
        return self.kube_delete_custom_object(
            group="ray.io",
            api_version="v1",
            plural="rayclusters",
            name=name,
            namespace=namespace
        )
    
    def get_pods_status_for_label(self, label_key, label_value, namespace):
        res = self.find_pods_with_label(
            label_key=label_key,
            label_value=label_value,
            namespace=namespace
        )
        pod_statuses = {}
        for pod in res.values():
            if pod["status"]["phase"] == "Running":
                status = "Ready" if all([s["ready"] for s in pod["status"]["container_statuses"]]) else "Working"
            else:
                status = pod["status"]["phase"]
            pod_statuses[pod["metadata"]["name"]] = {
                "status": status,
                "conditions": force_serialisation(pod["status"]["container_statuses"]),
                "node_name": pod["spec"]["node_name"]
            }

        return pod_statuses
    
    def get_ports_for_services(self, label_key:str, label_value=None, types=["NodePort"]):
        # pull only the service with the given label
        label_selector = label_key if label_value is None else f"{label_key}={label_value}"
        resources = self.core_api.list_service_for_all_namespaces(watch=False, label_selector=label_selector)
        service_ports = {}   
        def to_dict(service_port):
            return {
                "node_port": service_port.node_port,
                "port": service_port.port,
                "protocol": service_port.protocol,
                "target_port": service_port.target_port
            }
        if resources.items:
            for service in resources.items:
                if service.spec.type not in types:
                    continue
                service_ports[service.metadata.name] = {
                    "type": service.spec.type,
                    "ports": [to_dict(p) for p in service.spec.ports]
                }

        return service_ports
    
    def deploy_storage_claim(
            self,
            name: str,
            namespace: str,
            labels: dict,
            access_modes: list,
            storage_class_name: str,
            storage_size: int,
            **kwargs
    ):
        body = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=name,
                labels=labels
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=access_modes,
                storage_class_name=storage_class_name,
                resources=client.V1ResourceRequirements(
                    requests={"storage": f"{storage_size}Gi"}
                )
            )
        )
        result = self.core_api.create_namespaced_persistent_volume_claim(
            namespace,
            body
        )
        return force_serialisation(result)
    
    def deploy_service(
        self,
        name: str,
        namespace: str,
        labels: dict,
        selector_labels: dict,
        service_type: str,
        ports: list[dict],
        **kwargs
    ):
        body = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=name,
                labels=labels
            ),
            spec=client.V1ServiceSpec(
                ports=[client.V1ServicePort(**port) for port in ports],
                selector=selector_labels,
                type=service_type
            )
        )
        result = self.core_api.create_namespaced_service(
            namespace,
            body
        )
        return force_serialisation(result)
    
    def create_namespace(self, name, labels={}):
        if name in self.list_namespaces():
            return {"success": "already exists"}
        result = self.core_api.create_namespace(
            body=client.V1Namespace(
                metadata=client.V1ObjectMeta(name=name, labels=labels))
        )
        return force_serialisation(result)
    
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
    
    def get_storage_usage(self, namespace, target_storages: list=None):

        storages = defaultdict(dict)

        # get pvc statuses
        pvc_list = self.core_api.list_namespaced_persistent_volume_claim(namespace)

        for pvc in pvc_list.items:
            storages[pvc.metadata.name] = {
                "status": pvc.status.phase
            }

        # Fetch metrics
        response = requests.get(f"{LONGHORN_MANAGER_ENDPOINT}/metrics")
        if response.status_code != 200:
            print("Failed to fetch metrics:", response.text)
            exit()

        # Parse metrics to extract longhorn PVC details
        storage_capacity = extract_longhorn_metric_from_prometheus(
            metric_keys=["longhorn_volume_actual_size", "longhorn_volume_capacity_bytes"],
            map_fields={"longhorn_volume_actual_size": "used_capacity", "longhorn_volume_capacity_bytes": "total_capacity"},
            metrics=response.text
        )
        for pvc in storages:
            if pvc not in storage_capacity:
                storage_capacity[pvc] = {"used_capacity": 0, "total_capacity": 0}
            storages[pvc] = {**storages[pvc], **storage_capacity[pvc]}
            
        return {name: data for name, data in storages.items() if target_storages is None or name in target_storages}

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

    def delete_labeled_resources(self, namespace, label_key: str, label_value: str = None):
        """Delete all resources in a namespace with a given label"""

        core_api = client.CoreV1Api()
        apps_api = client.AppsV1Api()

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
            'persistentvolumeclaim': (core_api.list_namespaced_persistent_volume_claim, core_api.delete_namespaced_persistent_volume_claim),
            'leaderworkerset': (self.list_namespaced_lws, self.delete_namespaced_lws),
            'raycluster': (self.list_namespaced_raycluster, self.delete_namespaced_raycluster),
            'job': (self.list_namespaced_vcjob, self.delete_namespaced_vcjob)
        }

        for resource_type, (list_func, delete_func) in resource_types.items():
            try:
                resources = list_func(namespace, label_selector=label_selector)
                is_dict = isinstance(resources, dict)
                items = resources["items"] if is_dict else resources.items
                for resource in items:
                    name = resource["metadata"]["name"] if is_dict else resource.metadata.name
                    try:
                        delete_func(name=name, namespace=namespace)
                        deleted_resources.append(f"{resource_type}/{name}")
                    except Exception as e:
                        failed_resources.append(f"{resource_type}/{name}: {str(e)}")
            except Exception as e:
                print(f"Exception when listing {resource_type}: {e}")

        return {
            "deleted_resources": deleted_resources,
            "failures": failed_resources
        }
    
    ## DEPRECATED ##
        
    def deploy_generic_model(self, config: str, force_namespace: str="default"):
        # Deploy a generic config
        return self.kube_deploy_plus(
            yaml_strs=config,
            force_namespace=force_namespace)

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

    def find_nodeport_url(self, namespace:str, label_key:str, label_value=None):
        """ Termporary Way to find the nodeport url for a service with a given label"""

    
        # pull only the service with the given label
        label_selector = label_key if label_value is None else f"{label_key}={label_value}"

        service_ports = {}        

        resources = self.core_api.list_namespaced_service(namespace, label_selector=label_selector)
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

    res = api.get_pods_status_for_label(
        label_key="app",
        label_value="kube-watcher-api",
        namespace="kalavai"
    )
    print(json.dumps(res, indent=2))
