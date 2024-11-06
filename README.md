# Hermes

A single pane of glass for static code analysis

---

#### Local Development

Run `main.py` and either of the following:
```shell
docker compose -f ./docker-compose-dev.yml up hermes_saq hermes_redis hermes_db
docker compose -f ./docker-compose-dev.yml up --build hermes_saq hermes_redis hermes_db
```
