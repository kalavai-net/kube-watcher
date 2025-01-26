import yaml
import re

from kube_watcher.models import JobTemplate

from jinja2 import Template

TEMPLATE_ID_FIELD = "id_field"
TEMPLATE_ID_KEY = "deployment_id"
TEMPLATE_LABEL = "kalavai.job.name"
ENDPOINT_PORTS_KEY = "endpoint_ports"


def get_template_path(template: JobTemplate):
    return f"templates/{template.name}/template.yaml"

def get_defaults_path(template: JobTemplate):
    return f"templates/{template.name}/values.yaml"

def escape_field(text):
    return re.sub('[^0-9a-z]+', '-', text.lower())

class Job:
    def __init__(self, template: JobTemplate):
        if isinstance(template, str):
            template = JobTemplate[template]
        self.template = template
        self.template_str = self._load(template=template)
        self.job_name = None
        self.job_label = None
        self.ports = []

    def _load(self, template: JobTemplate):
        with open(get_template_path(template), "r") as f:
            return f.read()
        
    def get_defaults(self):
        with open(get_defaults_path(template=self.template), 'r') as f:
            default_values = yaml.safe_load(f)
        return default_values

    def populate(self, values: dict):
        default_values = self.get_defaults()
        
        # substitute missing values with defaults
        for default in default_values:
            if default["name"] == TEMPLATE_ID_FIELD:
                if default["default"] not in values:
                    raise ValueError(f"Key value '{default['default']}' missing from values")
                values[TEMPLATE_ID_KEY] = escape_field(values[default["default"]])
                continue
            if default["name"] not in values:
                values[default['name']] = default['default']
        self.job_name = values[TEMPLATE_ID_KEY]
        self.job_label = {TEMPLATE_LABEL: self.job_name}
        self.ports = values[ENDPOINT_PORTS_KEY].split(",")
        return Template(self.template_str).render(values)

        
if __name__ == "__main__":
    job = Job(template="aphrodite")
    job.populate(values={"model_id": "my_model"})
    print(job.job_name, job.ports)
    print([e.name for e in JobTemplate])