# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and to keep output unbuffered
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Update and install postgresql-client
RUN apt-get update && apt-get install -y postgresql-client

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only the dependency files to leverage Docker cache
COPY poetry.lock pyproject.toml /app/

# Install project dependencies
# --no-root: Do not install the project itself, only its dependencies
RUN poetry install --no-root

# Copy the rest of the application code
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

# Command to run the development server
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
