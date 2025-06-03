### Configuration Options

Note that project zip files currently enforce a maximum file size of `250 mb`. If you find yourself over this, consider using git or opening an issue at which point I can work to make it configurable.

#### Required
*These must be set for the application to function*

- `CSRF_TOKEN`: The token to use as the CSRF secret.
- `POSTGRES_DB`: The Postgres database to use.
- `POSTGRES_USER`: The Postgres user to auth as.
- `POSTGRES_PASSWORD`: The password for said Postgres user.
- `POSTGRES_HOST`: The host Postgres is running on.
- `POSTGRES_PORT`: The port for Postgres.
- `REDIS_URL`: The URL to use when attempting to connect to Redis.

#### Optional
*These are optional feature flags to provide*

- `DEBUG`: If set to a truthy value, dump tracebacks etc on error. Defaults to `false`
- `ALLOW_REGISTRATION`: Whether to let user's self sign up for accounts on the platform. Defaults to `true`. If you want to disable this, set it to `false`.
- `PROJECT_DIR`: The directory to store project files in. Defaults to `.projects`.
- `DISABLE_HIBP`: If set to a truthy value, bypass the Have I Been Pwned checks on passwords. Defaults to `false`.
- `DISABLE_AUTH`: If set to a truthy value, disable the requirement for authentication on the platform. Internally this sets everyone as a user without a usable password and automatically logs them in, although they don't have admin portal access. Defaults to `false`.

#### Developer Docker Compose Defaults

The following is an example `.env` file for the `docker-compose-dev.yml` file. It is recommended you change these values.

Set `CSRF_TOKEN` to the output of `openssl rand -hex 32`

```text
POSTGRES_DB=hermes_db
POSTGRES_USER=hermes_db_user
POSTGRES_PASSWORD=product-defeat-follow-worshiper-swimwear-drown
POSTGRES_HOST=localhost
POSTGRES_PORT=8801
CSRF_TOKEN=SETTHIS
PORT=8800
DEBUG=1
REDIS_URL=redis://default:haziness-sloppy-cycle-deduct-superman-undertook@localhost:8802/0
```

### Local Development

Run `main.py` with a configured `.env` and either of the following:
```shell
docker compose -f ./docker-compose-dev.yml up hermes_saq hermes_redis hermes_db
docker compose -f ./docker-compose-dev.yml up --build hermes_saq hermes_redis hermes_db
```