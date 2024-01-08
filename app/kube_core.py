import json
import time
import yaml
from collections import defaultdict

from kubernetes import config, client, utils
from kubernetes.dynamic import DynamicClient

from app.utils import create_deployment_yaml, RAY_DEPLOYMENT_TEMPLATE, DEFAULT_RAY_VALUES



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

        # CRD handling for
        self.k8s_client = client.api_client.ApiClient()
        self.dyn_client = DynamicClient(self.k8s_client)
    
    
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
            yaml_obj =  yaml.safe_load(yaml_str)
            # load kubernetes client
            k8s_client = client.api_client.ApiClient()
            # create pods from yaml object
            try:
                res = utils.create_from_yaml(
                    k8s_client,
                    yaml_objects=[yaml_obj],
                )
            except Exception as e:
                result = False
        return result
    

    def crd_kube_deploy(self, yaml_strs):
        yamls = yaml_strs.split("---")
        result = True
        k8s_client = client.api_client.ApiClient()
        dyn_client = DynamicClient(k8s_client)
        
        for yaml_str in yamls:
            yaml_obj = yaml.safe_load(yaml_str)
            try:
                gvr = dyn_client.resources.get(api_version=yaml_obj["apiVersion"], kind=yaml_obj["kind"])
                res = gvr.create(body=yaml_obj, namespace=yaml_obj.get("metadata", {}).get("namespace", "default"))
                print(res)
            except Exception as e:
                print(e)
                result = False
        return result
    
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
        yaml = create_deployment_yaml(
            values={
                "deployment_name": deployment_name,
                "model_id": model_id,
                "namespace": namespace,
                "num_cores": num_cores,
                "ephemeral_memory": ephemeral_memory,
                "ram_memory": ram_memory,
                "task": task,
                "replicas": replicas
            },
        )
        return self.kube_deploy(yaml)
    

        
    def deploy_ray_model(
        self,
        deployment_name,
        model_id,
        namespace,
        num_cpus=1,
        num_gpus=1,
        num_replicas=1
        # TODO ADD ARGS DICTS
    ):
        
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
        
        # Deploy a deepsparse model
        yaml = create_deployment_yaml(
            values={
                "deployment_name": deployment_name,
                "model_id": model_id,
                "namespace": namespace,
                "num_cpus": num_cpus,
                "num_gpus": num_gpus,
                "num_replicas":num_replicas
            },            
            default_values= DEFAULT_RAY_VALUES,
            template_file = RAY_DEPLOYMENT_TEMPLATE

        )
        return self.crd_kube_deploy(yaml)


    
    def list_deepsparse_deployments(self, namespace):
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
        # get nodeport services
        services = self.core_api.list_namespaced_service(namespace)
        for service in services.items:
            model_deployments[service.metadata.name]["cluster_ip"] = service.spec.cluster_ip
            model_deployments[service.metadata.name]["ports"] = [(port.node_port, port.target_port) for port in service.spec.ports]
        return model_deployments
    
    def delete_deepsparse_model(
        self,
        namespace,
        deployment_name
    ):
        k8s_apps = client.AppsV1Api()
        try:
            k8s_apps.delete_namespaced_deployment(f"{deployment_name}", namespace)
            self.core_api.delete_namespaced_service(f"{deployment_name}", namespace)
            return True
        except Exception as e:
            print("Exception when calling CoreV1Api->delete_namespaced_service: %s\n" % e)
            return False
    
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
    
    def list_ray_deployments(self, namespace=None):
        """
        Lists Ray model deployments deployed as CRDs.

        :param namespace: The namespace in which to list the Ray deployments.

        :return: A dictionary of Ray model deployments.
        """
        ray_deployments = defaultdict(dict)

        try:
            # Define the GVR for RayService
            ray_service_gvr = self.dyn_client.resources.get(api_version="ray.io/v1alpha1", kind="RayService")

            # List all RayService CRD instances in the specified namespace
            crd_instances = ray_service_gvr.get(namespace=namespace)

            for instance in crd_instances.items:
                # Extract relevant data from each RayService instance
                ray_deployments[instance.metadata.name] = {
                    "serviceUnhealthySecondThreshold": instance.spec.serviceUnhealthySecondThreshold,
                    "deploymentUnhealthySecondThreshold": instance.spec.deploymentUnhealthySecondThreshold,
                    "serveConfigV2": instance.spec.serveConfigV2,
                    "rayClusterConfig": instance.spec.rayClusterConfig,
                    # Add other relevant fields here
                }
        except Exception as e:
            print(f"Error listing Ray deployments: {e}")

        return ray_deployments
    
    def delete_ray_model(self, deployment_name, namespace=None):
        """
        Deletes a Ray CRD model.

        :param crd_name: The name of the Ray CRD model to delete.
        :param namespace: The namespace of the Ray CRD model.        

        :return: True if the deletion was successful, False otherwise.
        """
        try:
            # Define the GVR for RayService
            ray_service_gvr = self.dyn_client.resources.get(api_version="ray.io/v1alpha1", kind="RayService")

            # Delete the RayService CRD instance
            ray_service_gvr.delete(name=deployment_name, namespace=namespace)
            return True
        except Exception as e:
            print(f"Exception when trying to delete Ray CRD model: {e}")
            return False
        

if __name__ == "__main__":
    api = KubeAPI(in_cluster=False)
    
    res = api.list_deepsparse_deployments("kube-watcher")
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

    