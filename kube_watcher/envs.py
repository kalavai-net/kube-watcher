import os

LONGHORN_MANAGER_ENDPOINT = os.getenv("LONGHORN_MANAGER_ENDPOINT", "http://localhost:30132")
TEMPLATE_ID_LABEL = os.getenv("TEMPLATE_ID_LABEL", "kalavai.job.name")
TEMPLATE_CATEGORY_LABEL = os.getenv("TEMPLATE_CATEGORY_LABEL", "kalavai.job.category")
TEMPLATE_TYPE_LABEL = os.getenv("TEMPLATE_TYPE_LABEL", "kalavai.job.type")
KALAVAI_USER_KEY = os.getenv("KALAVAI_USER_KEY", "kalavai.cluster.user")
