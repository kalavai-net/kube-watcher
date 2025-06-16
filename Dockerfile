# Use an official Python runtime as a parent image
FROM python:3.9-slim

RUN apt update && apt install gcc g++ -y

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "kube_watcher.api:app", "--host", "0.0.0.0", "--port", "8000"]
