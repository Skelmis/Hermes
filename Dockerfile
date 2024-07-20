FROM python:3.10-slim

WORKDIR /code
RUN pip install poetry
COPY ./poetry.lock /code/poetry.lock

RUN poetry install

COPY . /code

RUN chmod +x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]
