FROM python:3.10-slim

# Ensure container is ready
RUN apt-get update; apt-get upgrade -y
RUN apt-get install -y git golang curl

WORKDIR /code
RUN pip install poetry

# Setup gosec
RUN curl -sfL https://raw.githubusercontent.com/securego/gosec/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v2.21.1
ENV PATH="/root/go/bin:$PATH"


# Program install steps
COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock

RUN poetry install

COPY . /code

RUN chmod +x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]
