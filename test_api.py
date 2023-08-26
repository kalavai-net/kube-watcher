import requests


URL = "http://localhost:8009"

if __name__ == "__main__":

    params = {
        "username": "carlos.fernandez.musoles@gmail.com",
        "password": ""
    }
    response = requests.get(
        f"{URL}/v1/validate_user",
        json=params
    )
    print(response.json())
    
    