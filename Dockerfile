# Use an official Python runtime as a parent image
FROM python:3.10-slim

LABEL org.opencontainers.image.source=https://github.com/kalavai-net/kube-watcher

RUN apt update && apt install curl gcc g++ -y

RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -e .

EXPOSE 8000
#CMD ["uvicorn", "kube_watcher.api:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "kube_watcher/api.py", "--host", "0.0.0.0", "--port", "8000"]