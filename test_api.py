import requests


URL = "http://159.65.30.72:31230"

if __name__ == "__main__":

    params = {
        "username": "carlos.fernandez.musoles@gmail.com",
        "password": "iekeopru"
    }
    response = requests.get(
        f"{URL}/v1/validate_user",
        json=params
    )
    print(response.json())
    
    