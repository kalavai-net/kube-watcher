# FROM python:3.9 as requirements-stage

# WORKDIR /tmp

# RUN pip install poetry
# COPY ./pyproject.toml ./poetry.lock* /tmp/
# RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# FROM python:3.9

# WORKDIR /code

# COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
# COPY ./app /code/app

# EXPOSE 8000
# CMD ["uvicorn", "kube_watcher.server:app", "--host", "0.0.0.0", "--port", "8000"]


# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "kube_watcher.server:app", "--host", "0.0.0.0", "--port", "8000"]
