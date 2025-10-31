from jinja2 import Template

template = """
{% if NODE_SELECTORS %}
nodeAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  #preferredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
  {% if NODE_SELECTORS_OPS == "OR" %}
    {% for selector in NODE_SELECTORS %}
    - matchExpressions:
      - key: {{selector.name}}
        operator: In
        values:
        {% for vals in selector.value %}
        - {{vals}}
        {% endfor %}
    {% endfor %}
  {% else %}
    - matchExpressions:
    {% for selector in NODE_SELECTORS %}
      {% for vals in selector.value %}
      - key: {{selector.name}}
        operator: In
        values:
        - {{vals}}
      {% endfor %}
    {% endfor %}
  {% endif %}
{% endif %}
"""


if __name__ == "__main__":
    doc = Template(
        template,
        trim_blocks=True,
        lstrip_blocks=True
    ).render(
        {
            "NODE_SELECTORS": [
                {
                    "name": "kalavai/job",
                    "value": ["gpu", "amd"]
                },
                {
                    "name": "kalavai/instance",
                    "value": ["high"]
                }
            ],
            "NODE_SELECTORS_OPS": "OR"
        }
    )
    print(doc)