"""

"""
from collections import defaultdict
import kubernetes.client
import kubernetes.config
from kubernetes.client.rest import ApiException
from pprint import pprint

from kube_watcher.utils import cast_resource_value


def get_nodes_status(api_instance, store_output_path=None, **kwargs):
    """Get the status of all nodes (list) in the kubernetes cluster"""
    try:
        # get connected nodes (capabilities and allocatable)
        api_response = api_instance.list_node(**kwargs)
        if store_output_path:
            with open(store_output_path, "w") as f:
                pprint(api_response, stream=f, compact=True)
        return api_response.items
    except ApiException as e:
        print("Exception when calling WellKnownApi->get_service_account_issuer_open_id_configuration: %s\n" % e)
        return None


def extract_cluster_capacity(nodes_status):
    """Extract total cluster capacity (from all nodes from get_nodes_status).
    - allocatable --> node resoures reported as allocatable
    - capacity --> nodes capacity as reported in capacity
    - online --> nodes capacity (for those with status Ready) as reported in capacity
    """
    data = {"allocatable": defaultdict(int), "capacity": defaultdict(int), "online": defaultdict(int)}
    for node in nodes_status:
        status = extract_node_status(node)
        for resource, value in status["allocatable"].items():
            data["allocatable"][resource] += cast_resource_value(value)
        for resource, value in status["capacity"].items():
            data["capacity"][resource] += cast_resource_value(value)
        if is_node_ready(node):
            for resource, value in status["capacity"].items():
                data["online"][resource] += cast_resource_value(value)
    return data

def extract_node_status(node_status):
    """Extract core information from a node status data (for each node from get_nodes_status)"""
    return node_status.status.to_dict()


def extract_node_id(node_status):
    """Get the node id (provider_id) from node status data (for each node from get_nodes_status)"""
    return node_status.spec.provider_id


def extract_node_readiness(node):
    """Extract the readiness of a node from its status information (from extract_node_status)"""
    for condition in node["conditions"]:
        if condition["type"] == "Ready":
            return condition
    return None


def is_node_ready(node):
    """Get the readiness status of a node (for a node from get_nodes_status)"""
    readiness = extract_node_readiness(extract_node_status(node))
    return readiness["status"] == "True"


if __name__ == "__main__":

    # # Enter a context with an instance of the API kubernetes.client
    kubernetes.config.load_kube_config("certs/cluster_config.yaml")
    with kubernetes.client.ApiClient() as api_client:
        # Create an instance of the API class
        api_instance = kubernetes.client.CoreV1Api(api_client)
        # watch allows to listen for updates (CRUD nodes, but status update does not show)
        nodes_status = get_nodes_status(api_instance, watch=False)
        capacity = extract_cluster_capacity(nodes_status)
        pprint(capacity)
        for idx, node_status in enumerate(nodes_status):
            print("---" * 20)
            node_id = extract_node_id(node_status)
            print(node_id)
            node = extract_node_status(node_status)
            print(extract_node_readiness(node))
            print(f"Is {node_id} ready --> {is_node_ready(node_status)}")

