import yaml
import json
import re
import copy
from os.path import commonprefix
import uuid

from kube_watcher.models import JobTemplate

from jinja2 import Template

TEMPLATE_ID_FIELD = "id_field"
TEMPLATE_ID_KEY = "deployment_id"
TEMPLATE_LABEL = "kalavai.job.name"
ENDPOINT_PORTS_KEY = "endpoint_ports"
NODE_SELECTOR = "NODE_SELECTORS"
NODE_SELECTOR_OPS = "NODE_SELECTORS_OPS"


def get_template_path(template: JobTemplate):
    return f"templates/{template.name}/template.yaml"

def get_defaults_path(template: JobTemplate):
    return f"templates/{template.name}/values.yaml"

def get_metadata_path(template: JobTemplate):
    return f"templates/{template.name}/metadata.json"

def escape_field(text):
    return re.sub('[^0-9a-z]+', '-', text.lower())

def parse_deployment_name(name, max_len=63, random_suffix=True):
    """Make it kubernetes ready:
    - Remove unacceptable characters
    - Make it less than 59 (accommodate for further replica suffixing)"""
    max_len = max_len if not random_suffix else max_len - 6
    escaped_name = escape_field(commonprefix(name.split(",")))[:max_len]
    if random_suffix:
        escaped_name += f"-{str(uuid.uuid4())[:6]}"

    return escaped_name

class Job:
    def __init__(self, template: JobTemplate, template_str: str=None):
        self.job_name = None
        self.job_label = None
        self.ports = []

        if template == JobTemplate.custom:
            # for custom jobs where we pass the template itself
            self.template_str = template_str
            self.template = template
        else:
            if isinstance(template, str):
                self.template = JobTemplate[template]
            self.template_str = self._load(template=self.template)

    @classmethod
    def from_yaml(cls, template_str):
        return cls(template=JobTemplate.custom, template_str=template_str)

    def _load(self, template: JobTemplate):
        with open(get_template_path(template), "r") as f:
            return f.read()
        
    def get_defaults(self):
        try:
            with open(get_defaults_path(template=self.template), 'r') as f:
                default_values = yaml.safe_load(f)
            return default_values
        except Exception as e:
            print("Error when getting defaults:", str(e))
            return None
    
    def get_metadata(self):
        try:
            with open(get_metadata_path(template=self.template), 'r') as f:
                meta = json.load(f)
            return meta
        except Exception as e:
            print("Error when getting metadata:", str(e))
            return None

    def populate(
        self, values: dict,
        default_values=None,
        target_labels=None,
        target_labels_ops="AND",
        replica=None,
        random_suffix=True
    ):
        if default_values is None:
            default_values = self.get_defaults()

        local_values = copy.deepcopy(values)
        local_default_values = copy.deepcopy(default_values)
        for default in local_default_values:
            # scan for template id field (name of the job)
            if default["name"] == TEMPLATE_ID_FIELD:
                if default["default"] not in local_values:
                    raise ValueError(f"Key value '{default['default']}' missing from values")
                if replica is not None:
                    local_values[TEMPLATE_ID_KEY] = parse_deployment_name(
                        name=local_values[default["default"]], 
                        random_suffix=random_suffix,
                        max_len=58) + f"-{replica}"
                else:
                    local_values[TEMPLATE_ID_KEY] = parse_deployment_name(
                        name=local_values[default["default"]],
                        random_suffix=random_suffix)
                continue
            # substitute missing values with defaults
            if default["name"] not in local_values:
                local_values[default['name']] = default['default']
            else:
                # check that non editable fields are not present
                if "editable" in default and not default["editable"]:
                    print(f"Removing non editable field [{default['name']}]")
                    del local_values[default['name']]

        self.job_name = local_values[TEMPLATE_ID_KEY]
        self.job_label = {TEMPLATE_LABEL: self.job_name}
        self.ports = local_values[ENDPOINT_PORTS_KEY].split(",") if ENDPOINT_PORTS_KEY in local_values else []
        if target_labels is not None:
            local_values[NODE_SELECTOR] = [
                {"name": key, "value": value if isinstance(value, list) else [value]} 
                for key, value in target_labels.items()
            ]
            local_values[NODE_SELECTOR_OPS] = target_labels_ops

        return Template(self.template_str, lstrip_blocks=True, trim_blocks=True).render(local_values)

        
if __name__ == "__main__":
    job = Job(template="playground")
    print(job.get_defaults())
    