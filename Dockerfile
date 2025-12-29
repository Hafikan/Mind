FROM python:3.14.2-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PTHONUNBUFFERED=1

WORKDIR /code
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 
COPY . .

