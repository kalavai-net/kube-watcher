"""
How to create a token: https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/#without-kubectl-proxy

"""

import kubernetes.client
import time
from kubernetes.client.rest import ApiException
from pprint import pprint


if __name__ == "__main__":
    configuration = kubernetes.client.Configuration()
    # Configure API key authorization: BearerToken
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNjclFFTGxYdDZObzVGbF9FWXFHU0o2YVdjZ3RpaTRrVkhnZ1NyaE5RS0UifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwiLCJrM3MiXSwiZXhwIjoxNjg1ODIyMjc3LCJpYXQiOjE2ODU4MTg2NzcsImlzcyI6Imh0dHBzOi8va3ViZXJuZXRlcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsIiwia3ViZXJuZXRlcy5pbyI6eyJuYW1lc3BhY2UiOiJrdWJlcm5ldGVzLWRhc2hib2FyZCIsInNlcnZpY2VhY2NvdW50Ijp7Im5hbWUiOiJhZG1pbi11c2VyIiwidWlkIjoiYmU0Yzc4MWItY2ZiNC00ODEwLTlmNDItZTc3NmJiOGFjODQwIn19LCJuYmYiOjE2ODU4MTg2NzcsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlcm5ldGVzLWRhc2hib2FyZDphZG1pbi11c2VyIn0.1Sg3V3xuGJV_mBfc8fcAlAGuWTzEZk917k0epbr88_EEFvUPc7IyhEcauiQpaEAPV_tGFdrisqV87eXVhDZNj8ZkdxMIJVzzIQ80YnhDS1ETLxPN3p7a33y2XXiL1thytwv7onf4vOvqOJ4wbHYGzEjE_Yt0DY0Kh0Yyal-sJNpG-RneL7iM6CydCwaBsLtnNM3trVekuE8ZrB1BqwOtcyfALTUPMGEvnm8G4ow7ag81PVF_lilQfoRWKddHT3eEatmvZdtxijM6nXVPyvCZUTKuJ01MtoDqSe6hArQ_8LDv0SH3B4lvGUZZyI6pdO38SMhkcFNTqYV9QhxLfgC_uw"
    
    # Defining host is optional and default to http://localhost
    configuration.host = "https://10.8.0.1:6443"
    configuration.verify_ssl = False
    configuration.api_key = {"authorization": "Bearer " + token}


    # Enter a context with an instance of the API kubernetes.client
    with kubernetes.client.ApiClient(configuration) as api_client:

        # Create an instance of the API class
        api_instance = kubernetes.client.WellKnownApi(api_client)       
        try:
            api_response = api_instance.get_service_account_issuer_open_id_configuration()
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling WellKnownApi->get_service_account_issuer_open_id_configuration: %s\n" % e)