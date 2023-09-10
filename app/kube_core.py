import json
from collections import defaultdict

from kubernetes import config, client


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
        self.api = client.CoreV1Api()
    
    
    def extract_node_readiness(self, node):
        """Extract the readiness of a node from its status information (from extract_node_status)"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition
        return None
    
    def _extract_resources(self, fn):
        """Generalisation to extract values in dict form"""
        nodes = self.api.list_node()
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


if __name__ == "__main__":
    api = KubeAPI(in_cluster=False)
    
    values = api.extract_cluster_labels()
    print(json.dumps(values, indent=3))
    
    labels = api.get_node_labels()
    print(json.dumps(labels, indent=3))

    