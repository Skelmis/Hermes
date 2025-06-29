FROM ghcr.io/astral-sh/uv:python3.10-alpine

# Ensure container is ready
RUN apk update
RUN apk add git go curl bash ruby-dev make

WORKDIR /code

### Setup gosec
RUN curl -sfL https://raw.githubusercontent.com/securego/gosec/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v2.22.5
ENV PATH="/root/go/bin:$PATH"

### Setup brakeman
RUN gem install brakeman


## Program install steps
COPY ./pyproject.toml /code/pyproject.toml
COPY ./uv.lock /code/uv.lock

RUN uv sync --compile-bytecode
RUN uv pip install semgrep

COPY . /code

RUN chmod +x /code/docker/saq/entrypoint.sh
ENTRYPOINT ["/code/docker/saq/entrypoint.sh"]
