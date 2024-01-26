from string import Template


DEFAULT_DEEPSPARSE_VALUES = {
    'num_cores': '4',
    "ram_memory": "14Gi",
    "ephemeral_memory": "48Gi"
}
DEPLOYMENT_TEMPLATE = "app/deployment_template.yaml"


def create_deployment_yaml(values, template_file=DEPLOYMENT_TEMPLATE):
    """
    generates a yaml deployment file for a deepsparse model serving
    """
    for key, value in DEFAULT_DEEPSPARSE_VALUES.items():
        if key not in values:
            values[key] = value
            print(f"{key} not found, using default value {value}")
    
    with open(template_file, 'r') as f:
        src = Template(f.read())
        result = src.substitute(values)
        print(result)
    return result