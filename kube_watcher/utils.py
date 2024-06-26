from string import Template
from collections import defaultdict


DEEPSPARSE_DEFAULT_VALUES = {
    'num_cores': '4',
    "ram_memory": "14Gi",
    "ephemeral_memory": "48Gi"
}
DEEPSPARSE_DEPLOYMENT_TEMPLATE = "deployments/deepsparse_deployment_template.yaml"
FLOW_DEPLOYMENT_TEMPLATE = "deployments/flow_deployment_template.yaml"
AGENT_BUILDER_TEMPLATE = "deployments/agent_builder_template.yaml"


def cast_resource_value(value):
    """Cast string returned from reported node allocatable/capacity to int.
    
    Examples:
    - '12'
    - '121509440008'
    - '16288096Ki'
    """
    if value.endswith('Ki'):
        return int(value[:-2]) * 1024
    elif value.endswith('Mi'):
        return int(value[:-2]) * 1024 * 1024
    elif value.endswith('Gi'):
        return int(value[:-2]) * 1024 * 1024 * 1024
    elif value.endswith('m'):
        return int(value[:-1]) / 1000
    elif value.endswith('M'):
        return int(value[:-1]) * 1000000
    elif value.endswith('G'):
        return int(value[:-1]) * 1000000000
    else:
        return int(value)


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


def create_deployment_yaml(values, template_file, default_values=None):
    """
    generates a yaml deployment file for a templated deployment
    """
    if default_values is not None:
        for key, value in default_values.items():
            if key not in values:
                values[key] = value
                print(f"{key} not found, using default value {value}")
    with open(template_file, 'r') as f:
        src = Template(f.read())
        result = src.substitute(values)
    return result


def create_deepsparse_yaml(values, template_file=DEEPSPARSE_DEPLOYMENT_TEMPLATE, default_values=DEEPSPARSE_DEFAULT_VALUES):
    """
    generates a yaml deployment file for a deepsparse model serving
    """
    
    return create_deployment_yaml(values, template_file=template_file, default_values=default_values)


def create_flow_deployment_yaml(values, template_file=FLOW_DEPLOYMENT_TEMPLATE, default_values=None):
    """
    generates a yaml deployment file for a langflow serving
    """
    return create_deployment_yaml(values, template_file=template_file, default_values=default_values)


def create_agent_builder_deployment_yaml(values, template_file=AGENT_BUILDER_TEMPLATE, default_values=None):
    """
    generates a yaml deployment file for a langflow serving
    """
    return create_deployment_yaml(values, template_file=template_file, default_values=default_values)

