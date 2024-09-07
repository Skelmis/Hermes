FROM python:3.10-slim

# Ensure container is ready
RUN apt-get update; apt-get upgrade -y
RUN apt-get install -y git golang
RUN wget -O - -q https://raw.githubusercontent.com/securego/gosec/master/install.sh | sh -s vX.Y.Z


# Program install steps
WORKDIR /code
RUN pip install poetry
COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock

RUN poetry install

COPY . /code

RUN chmod +x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]
