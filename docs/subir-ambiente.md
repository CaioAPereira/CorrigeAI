# Subir o ambiente (dia a dia)

Passo a passo para levantar o CorrigeAI depois que o setup inicial já foi feito
(Laravel instalado, `.env` configurado, imagens já buildadas ao menos uma vez).

## 1. Ir para a raiz do projeto

O `docker-compose.yml` fica na raiz, não dentro de `src/`.

```bash
cd ~/CorrigeAI
```

## 2. Subir os containers

```bash
docker compose up -d
```

Só use `--build` se você alterou algum Dockerfile (`docker/php`, `docker/python`)
ou dependências (composer.json, requirements.txt):

```bash
docker compose up -d --build
```

## 3. Conferir se todos subiram

```bash
docker compose ps
```

O `db` precisa estar `healthy` — os outros serviços esperam isso automaticamente
antes de subir (`depends_on: condition: service_healthy`).

## 4. Rodar as migrations pendentes

Sempre que houver migration nova (ex: depois de um `git pull`):

```bash
docker compose exec app php artisan migrate
```

## 5. Validar que está tudo no ar

```bash
docker compose logs -f app          # Ctrl+C para sair
curl http://localhost:8080          # aplicação Laravel
curl http://localhost:8000/health   # serviço OCR
```

| Serviço | URL |
|---|---|
| Aplicação Laravel | http://localhost:8080 |
| API do leitor óptico (Swagger) | http://localhost:8000/docs |
| PostgreSQL (DBeaver) | `localhost:5432` — `corrigeai` / `corrigeai` / `secret` |

## Comandos úteis

```bash
docker compose ps                                   # status dos containers
docker compose logs -f app                           # logs do Laravel
docker compose logs -f ocr                            # logs do FastAPI
docker compose exec app php artisan migrate:status    # ver quais migrations rodaram
docker compose exec app php artisan migrate:fresh     # recria o schema do zero
docker compose exec db psql -U corrigeai -d corrigeai # console do Postgres
docker compose down                                   # derruba (mantém o volume do banco)
docker compose down -v                                # derruba e APAGA o banco
```

## Encerrar o trabalho

```bash
docker compose down
```

Isso mantém o volume do Postgres (`pgdata`) intacto — os dados continuam lá
na próxima vez que subir com `docker compose up -d`.
