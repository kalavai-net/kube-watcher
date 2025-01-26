import yaml
import json


RAY_LABEL = "kalavai.ray.name"

class RayCluster:
    def __init__(self, name, manifest):
        self.body = yaml.safe_load(manifest)
        # ensure deployment is labelled (for tracking and deletion)
        if "metadata" not in self.body:
            self.body["metadata"] = {}
        self.body["metadata"]["name"] = name
        if "labels" in self.body["metadata"]:
            self.body["metadata"]["labels"][RAY_LABEL] = name
        else:
            self.body["metadata"]["labels"] = {
                RAY_LABEL: name
            }
        self.body = json.dumps(self.body, indent=3)