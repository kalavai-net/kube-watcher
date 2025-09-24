# Download from civitai
# https://education.civitai.com/civitais-guide-to-downloading-via-api/
import argparse
import requests
import os


BASE_URL = "https://civitai.com/api/v1"
API_KEY = os.getenv("CIVITAI_API_KEY", "")


def download_model(model_id, output_dir="./"):
    # get download link
    response = requests.get(
        url=f"{BASE_URL}/models/{model_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    models = response.json()
    for file in models["modelVersions"][0]["files"]:
        print("Downloading ", file["name"])
        with requests.get(url=file["downloadUrl"], headers={"Authorization": f"Bearer {API_KEY}"}, stream=True) as r:
            r.raise_for_status()
            with open(os.path.join(output_dir, file["name"]), "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id")
    parser.add_argument("--output_dir")

    args = parser.parse_args()
    download_model(model_id=args.model_id, output_dir=args.output_dir)