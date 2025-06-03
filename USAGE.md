### Quick Start Guide

1. `git clone https://github.com/Skelmis/Hermes.git hermes`
2. `cd hermes`
3. `docker compose -f ./docker-compose-dev.yml up`
4. Navigate to http://127.0.0.1:8800
5. Create an account and you are good to go.

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
- `SERVING_DOMAIN`: The domain this site will run on. Used for cookies etc.

#### Optional
*These are optional feature flags to provide*

- `DEBUG`: If set to a truthy value, dump tracebacks etc on error. Defaults to `false`
- `ALLOW_REGISTRATION`: Whether to let user's self sign up for accounts on the platform. Defaults to `true`. If you want to disable this, set it to `false`.
- `PROJECT_DIR`: The directory to store project files in. Defaults to `.projects`.
- `DISABLE_HIBP`: If set to a truthy value, bypass the Have I Been Pwned checks on passwords. Defaults to `false`.
- `DISABLE_AUTH`: If set to a truthy value, disable the requirement for authentication on the platform. Internally this sets everyone as a shared user without a usable password and automatically logs them in, although they don't have admin portal access. Defaults to `false`.

#### Developer Docker Compose Defaults

The following is an example `.env` file for the `docker-compose-dev.yml` file when used in conjunction with the [Local Development](#local-development) commands. It is recommended you change these values.

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

#### Local Development

Run `main.py` with a configured `.env` and either of the following:
```shell
docker compose -f ./docker-compose-dev.yml up hermes_saq hermes_redis hermes_db
docker compose -f ./docker-compose-dev.yml up --build hermes_saq hermes_redis hermes_db
```

### Deployment Hardening

While efforts have been taken to secure this application, it is inherently a tool that wraps command line scanners and stores project files on disk.

It is recommended that if you do wish to deploy this outside of your own laptop that the following conditions are met:
- Ensure debug mode is not enabled
- Disable user sign up (`ALLOW_REGISTRATION=false`)
- Ensure platform users are considered relatively trusted (I.e. friends, other internal users on the lan, etc)
- Set strong passwords for Postgres and Redis as well as ensuring they are only exposed to the local network
- Set a strong CSRF token

If you encounter security issues when deploying in environments that meet the above expectations I'd love to hear about it! When doing so please follow the security policy located [here](https://github.com/Skelmis/Hermes/security/policy).

#### User Model

There are three types of user's within the application. These are Regular Users, Admins and Superusers.

###### Regular Users

The bread and butter of users. Can use all the application besides the admin panel.

###### Admins

Same as Regular Users but also have access to the admin panel at `/admin/`.

###### Superusers

Same as Admins but they can also create new users via the admin panel. Basically a requirement if self sign up is turned off.

Creating users via the command line is also possible with the command `uv run piccolo user create` within the web applications Docker image.