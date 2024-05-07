import json
import time
import yaml
from collections import defaultdict

from kubernetes import config, client, utils

from kube_watcher.utils import (
    create_deepsparse_yaml,
    create_flow_deployment_yaml
)


def cast_resource_value(value):
    """Cast string returned from reported node allocatable/capacity to int.
    
    Examples:
    - '12'
    - '121509440008'
    - '16288096Ki'
    """
    try:
        if "Ki" in value:
            value = int(value.replace("Ki", "")) * 1000
            return value
        else:
            return int(value)
    except:
        return None


def parse_resource_value(resources, out_data_dict=None):
    """Parse values reported by Kube API and get int amounts.
    If it is not an int, ignore
    
    Example
    
    {
        'cpu': '12',
        'ephemeral-storage': '121509440008',
        'hugepages-1Gi': '0',
        'hugepages-2Mi': '0',
        'memory': '16288096Ki',
        'nvidia.com/gpu': '1',
        'pods': '110'
    }
    """
    if out_data_dict is None:
        out_data_dict = defaultdict(int)
    
    for resource, value in resources.items():
        parsed_value = cast_resource_value(value)
        if parsed_value is not None:
            out_data_dict[resource] += parsed_value
    return out_data_dict



class KubeAPI():
    def __init__(self, in_cluster=False):
        if in_cluster:
            config.load_incluster_config()
        else:
            # Only works if this script is run by K8s as a POD
            config.load_kube_config()
        self.core_api = client.CoreV1Api()
    
    
    def extract_node_readiness(self, node):
        """Extract the readiness of a node from its status information (from extract_node_status)"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition
        return None
    
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


    def extract_cluster_capacity(self):
        """Extract total cluster capacity (from all nodes from get_nodes_status).
        - total --> nodes capacity as reported in capacity
        - online --> nodes capacity (for those with status Ready) as reported in capacity
        """
        fn = lambda node: node.status.capacity
        return self._extract_resources(fn=fn)
    
    def extract_cluster_labels(self):
        """Similar to extract_cluster_capacity but with node labels.
        - total --> nodes labels as reported in node labels
        - online --> nodes labels (for those with status Ready) as reported in node labels
        """
        fn = lambda node: node.metadata.labels
        return self._extract_resources(fn=fn)

    def get_node_labels(self, node_names=None):
        nodes = self.api.list_node()
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
    
    def deploy_flow(
        self,
        deployment_name,
        namespace,
        flow,
        api_key,
        num_cores=2,
        ram_memory="2Gi",
        replicas=1
    ):
        # Deploy a deepsparse model
        yaml = create_flow_deployment_yaml(
            values={
                "deployment_name": deployment_name,
                "username": namespace,
                "flow": json.dumps(flow),
                "num_cores": num_cores,
                "ram_memory": ram_memory,
                "replicas": replicas,
                "api_key": api_key
            }
        )
        return self.kube_deploy(yaml)
    
    def delete_flow(
        self,
        deployment_name,
        namespace
    ):
        """Delete a flow deployment within a namespace.
        
        TODO: at the moment it deletes everything within the namespace. Be more surgical
        """
        try:
            # TODO create a CRD for flow deployments so we don't have to delete individual components
            # config map
            self.core_api.delete_namespaced_config_map(name=f"{deployment_name}-configmap", namespace=namespace)
            # service
            self.core_api.delete_namespaced_service(name=f"{deployment_name}-service", namespace=namespace)
            # deployment
            apps_api = client.AppsV1Api(client.api_client.ApiClient())
            apps_api.delete_namespaced_deployment(name=f"{deployment_name}-flow", namespace=namespace)
            # ingress
            network_api = client.NetworkingV1Api(client.api_client.ApiClient())
            network_api.delete_namespaced_ingress(name=f"{deployment_name}-ingress", namespace=namespace)
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
    
    
    ## DEPRECATED ##
    
    def deploy_deepsparse_model(
        self,
        deployment_name,
        model_id,
        namespace,
        num_cores,
        ephemeral_memory,
        ram_memory,
        task,
        replicas
    ):
        # Deploy a deepsparse model
        yaml = create_deepsparse_yaml(
            values={
                "deployment_name": deployment_name,
                "model_id": model_id,
                "namespace": namespace,
                "num_cores": num_cores,
                "ephemeral_memory": ephemeral_memory,
                "ram_memory": ram_memory,
                "task": task,
                "replicas": replicas
            }
        )
        return self.kube_deploy(yaml)
    
    def list_deepsparse_deployments(self, namespace):
        return self.list_deployments(namespace=namespace, inspect_services=True)

    def delete_deepsparse_model(
        self,
        namespace,
        deployment_name
    ):
       return self.delete_deployment(
            namespace=namespace,
            deployment_name=deployment_name
       )

    def delete_deployment(
        self,
        namespace,
        deployment_name
    ):
        k8s_apps = client.AppsV1Api()
        try:
            k8s_apps.delete_namespaced_deployment(deployment_name, namespace)
            self.core_api.delete_namespaced_service(deployment_name, namespace)
            return True
        except Exception as e:
            print(f"Exception when calling CoreV1Api->delete_namespaced_service: {str(e)}")
    
    def create_ray_cluster(self, namespace, cluster_config=None, nodeport_config=None):
        # TODO:
        # - Create a ray cluster in the user namespace
        try:
            print("Creating namespace...")
            result = self.core_api.create_namespace(
                body=client.V1Namespace(
                    metadata={"name": namespace}
                )
            )
            print(result)
        except:
            # skip if already present
            pass

        if cluster_config:
            print("Creating ray cluster...")
            with open(cluster_config, 'r') as yaml_in:
                yaml_object = yaml.safe_load(yaml_in) # yaml_object will be a list or a dict
            
            result = client.CustomObjectsApi().create_namespaced_custom_object(
                group="ray.io", 
                version="v1alpha1",
                namespace=namespace,
                plural="rayclusters",
                body=yaml_object,
                pretty=True
            )
            print(result)
        
        # - create a nodeport service to access the cluster
        if nodeport_config:
            print("Creating ray nodeport...")
            with open(nodeport_config, 'r') as yaml_in:
                yaml_object = yaml.safe_load(yaml_in) # yaml_object will be a list or a dict
            
            result = api.core_api.create_namespaced_service(
                namespace=namespace,
                body=yaml_object,
                pretty=True
            )
            print(result)
        # - return connection details via the nodeport
        return result
        
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
    
    res = api.delete_flow(deployment_name="my-deployment-flow", namespace="carlosfm")
    print(res)
    exit()
    with open("Chatbot.json", "r") as f:
        flow = json.load(f)
    res = api.deploy_flow(
        deployment_name="my-deployment-flow",
        namespace="carlosfm",
        flow=flow,
        api_key="None")
    print(res)
    
    exit()
    result = api.create_ray_cluster(
        namespace="carlos-ray",
        cluster_config="data/ray_cluster.yaml",
        nodeport_config="data/ray_nodeport.yaml"
    )
    
    # Get custom objects that match:
    #apiVersion: ray.io/v1alpha1
    #kind: RayCluster
    clusters = client.CustomObjectsApi().list_cluster_custom_object(
        group="ray.io", 
        version="v1alpha1",
        plural="rayclusters")
    for item in clusters["items"]:
        print(json.dumps(item, indent=3))
    exit()
    
    values = api.extract_cluster_labels()
    print(json.dumps(values, indent=3))
    
    labels = api.get_node_labels()
    print(json.dumps(labels, indent=3))

    