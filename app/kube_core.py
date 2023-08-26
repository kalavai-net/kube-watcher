from collections import defaultdict

from kubernetes import config


def load_config(in_cluster=False):
    if in_cluster:
        config.load_incluster_config()
    else:
        # Only works if this script is run by K8s as a POD
        config.load_kube_config()


def cast_resource_value(value):
    """Cast string returned from reported node allocatable/capacity to int.
    
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
    try:
        if "Ki" in value:
            value = int(value.replace("Ki", "")) * 1000
            return value
        else:
            return int(value)
    except:
        return 0
    
def extract_node_readiness(node):
    """Extract the readiness of a node from its status information (from extract_node_status)"""
    for condition in node.status.conditions:
        if condition.type == "Ready":
            return condition
    return None


def extract_cluster_capacity(nodes):
    """Extract total cluster capacity (from all nodes from get_nodes_status).
    - allocatable --> node resoures reported as allocatable
    - capacity --> nodes capacity as reported in capacity
    - online --> nodes capacity (for those with status Ready) as reported in capacity
    """
    data = {"online": defaultdict(int), "total": defaultdict(int)}
    for node in nodes:
        status = True if extract_node_readiness(node).status == "True" else False
        if status:
            data["online"]["n_nodes"] += 1
            for resource, value in node.status.capacity.items():
                data["online"][resource] += cast_resource_value(value)
        data["total"]["n_nodes"] += 1
        for resource, value in node.status.capacity.items():
            data["total"][resource] += cast_resource_value(value)
    return data