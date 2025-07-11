"""
Example on how to interact with the n8n workflow API

More info on how to configure webhooks:
https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/#supported-authentication-methods
"""

import requests

API_BASE_URL = "http://localhost:31684"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0ZTY3MDA1YS02N2JmLTRhNDItOWFmZi0zZWJhNDgxNWE4NmEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUyMjI2NDc1fQ.TYS-aPmbZCizNF29rJqTpsbmsD2vkQBpyEc6nHKERD0"
WEBHOOK_AUTH_KEY_NAME = "Auth_key"
WEBHOOK_AUTH_KEY_VALUE = "sk-25021984"


def test_n8n_api():
    response = requests.get(
        f"{API_BASE_URL}/api/v1/workflows",
        headers={"X-N8N-API-KEY": API_KEY}
    )
    response.raise_for_status()
    return response.json()

def test_webhook():
    response = requests.get(
        f"{API_BASE_URL}/webhook/data",
        headers={WEBHOOK_AUTH_KEY_NAME: WEBHOOK_AUTH_KEY_VALUE}
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    print(
        "Webhook:",
        test_webhook()
    )

    print(
        "N8N API get workflows",
        test_n8n_api()
    )
