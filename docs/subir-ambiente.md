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

## 6. Assets front-end (Node/npm)

**Roda no host (WSL2), nunca dentro do container `app`.** O container `app`
só tem PHP-FPM — não tem Node instalado, e não precisa: o Vite gera arquivos
estáticos em `public/build/`, que o container já enxerga via volume montado
do `src/`.

Primeira vez, ou depois de mudar `package.json`:

```bash
cd ~/CorrigeAI/src
npm install
```

Compilar assets (uma vez, gera `public/build/`):

```bash
npm run build
```

Durante desenvolvimento ativo (recompila sozinho a cada mudança em `resources/`):

```bash
npm run dev
```

**Regra geral do projeto:** comandos `php artisan` / `composer` sempre via
`docker compose exec app ...` (o host roda PHP 8.3, o Laravel 13 exige 8.4+,
que só existe na imagem do container). Comandos `npm` sempre direto no host
(o container não tem Node). Nunca misture os dois.

## 7. Script standalone de leitura (sem Docker)

Via alternativa ao serviço HTTP, para rodar a leitura do gabarito isolada,
direto no PC com Python (ex.: se o trabalho pedir um script à parte em vez
da aplicação completa). É o arquivo `ocr-service/ler_gabarito.py` **sozinho**
— não depende de `omr.py`, FastAPI, Docker nem de nenhum outro arquivo do
projeto. Basta copiar esse único arquivo para qualquer PC com Python 3.10+:

```bash
pip install opencv-python-headless numpy
python3 ler_gabarito.py caminho/para/foto-do-gabarito.png
```

Testado rodando em container `python:3.12-slim` limpo, só com o arquivo
`ler_gabarito.py` e as duas dependências acima instaladas via pip.

O script pergunta a alternativa correta de cada questão (guardada só em
memória, nesta execução), lê a imagem e mostra questão a questão o que foi
marcado, o que era esperado, e o total de acertos.

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
