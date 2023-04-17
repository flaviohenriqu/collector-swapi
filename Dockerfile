FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

COPY poetry.lock pyproject.toml /usr/src/app/

RUN pip3 install poetry

RUN poetry install
