FROM python:3.10-alpine

# Ensure container is ready
RUN apk update
RUN apk add git go curl bash ruby-dev make

WORKDIR /code
RUN pip install poetry

### Setup gosec
RUN curl -sfL https://raw.githubusercontent.com/securego/gosec/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v2.21.1
ENV PATH="/root/go/bin:$PATH"

### Setup brakeman
RUN gem install brakeman


## Program install steps
COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock

RUN poetry install

COPY . /code

RUN chmod +x /code/docker/saq/entrypoint.sh
ENTRYPOINT ["/code/docker/saq/entrypoint.sh"]
