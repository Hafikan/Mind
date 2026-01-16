FROM python:3.14.2-slim-bookworm

#Deny the Python from wtiring pyc files in container
ENV PYTHONDONTWRITEBYTECODE=1
#Deny the  Python stout buffer
ENV PYTHONBUFFERED=1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code 
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./Mind ./
EXPOSE 8080 