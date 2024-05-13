from string import Template


DEEPSPARSE_DEFAULT_VALUES = {
    'num_cores': '4',
    "ram_memory": "14Gi",
    "ephemeral_memory": "48Gi"
}
DEEPSPARSE_DEPLOYMENT_TEMPLATE = "deployments/deepsparse_deployment_template.yaml"
FLOW_DEPLOYMENT_TEMPLATE = "deployments/flow_deployment_template.yaml"
AGENT_BUILDER_TEMPLATE = "deployments/agent_builder_template.yaml"


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

