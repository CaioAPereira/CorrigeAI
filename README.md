# CorrigeAI

A simple test corrector.

Sistema de leitura e correção de gabaritos (OMR — Optical Mark Recognition).
Prova de formato fixo: **8 questões, 4 alternativas (A, B, C, D)**.

## Arquitetura

Dois serviços independentes, separados por responsabilidade:

- **Aplicação principal** — Laravel 13 + Livewire 4 + Nginx + PostgreSQL 16.
  Guarda os gabaritos oficiais e executa a **regra de negócio** (comparação e nota).
- **Leitor óptico** — Python + FastAPI + OpenCV.
  Recebe a imagem e devolve o que o aluno marcou. **Não conhece gabarito, não calcula nota, não acessa banco.**

```
Livewire --(POST multipart: só a imagem)--> FastAPI
         <--(JSON: {"1":"A","2":"C","3":null,...})--
   |
   +--> compara com answer_keys (PostgreSQL) --> nota
```

## Pré-requisito

**Docker Engine no WSL2** (Ubuntu). Não precisa de Docker Desktop.
Verifique com `docker --version` e `docker compose version` dentro do WSL.

> Todos os comandos abaixo rodam **dentro do WSL**.
> Do PowerShell, use: `wsl -e bash -lc 'comando'`

## Subindo o projeto

### 1. Instalar o Laravel dentro de `src/` (só na primeira vez)

```bash
docker run --rm -v "$(pwd):/app" -w /app composer:2   create-project laravel/laravel:^13.0 src --no-interaction
docker run --rm -v "$(pwd)/src:/app" -w /app composer:2   require livewire/livewire --no-interaction
```

### 2. Subir os containers

```bash
docker compose up -d --build
```

O primeiro build demora — compila extensões PHP e instala OpenCV.

### 3. Configurar o .env do Laravel

Edite `src/.env` e ajuste o bloco do banco (o compose já injeta essas vars,
mas o Laravel lê o arquivo):

```
DB_CONNECTION=pgsql
DB_HOST=db
DB_PORT=5432
DB_DATABASE=corrigeai
DB_USERNAME=corrigeai
DB_PASSWORD=secret

OCR_SERVICE_URL=http://ocr:8000
```

> `DB_HOST=db` e `OCR_SERVICE_URL=http://ocr:8000` usam os **nomes dos serviços**
> do compose. Dentro da rede do Docker, `localhost` é o próprio container — não funcionaria.

### 4. Rodar as migrations

> **Obrigatório.** O `create-project` roda as migrations contra SQLite, não contra
> o Postgres do container. Sem este passo a aplicação devolve **HTTP 500**
> (`SQLSTATE[42P01]: Undefined table`), porque `SESSION_DRIVER=database`
> exige a tabela `sessions`.

```bash
docker compose exec app php artisan migrate
```

## Acessos

| Serviço | URL |
|---|---|
| Aplicação Laravel | http://localhost:8080 |
| API do leitor óptico (Swagger) | http://localhost:8000/docs |
| PostgreSQL (DBeaver) | `localhost:5432` — `corrigeai` / `corrigeai` / `secret` |

## Comandos do dia a dia

```bash
docker compose ps                      # status dos containers
docker compose logs -f app             # logs do Laravel
docker compose logs -f ocr             # logs do FastAPI
docker compose exec app php artisan migrate:fresh   # recria o schema
docker compose exec db psql -U corrigeai -d corrigeai  # console do Postgres
docker compose down                    # derruba (mantém o volume do banco)
docker compose down -v                 # derruba e APAGA o banco
```

## Performance no WSL2

O projeto em `/mnt/c/...` é acessado pelo WSL via 9p, lento para muitos arquivos
pequenos: **~5s por request**. Funciona, mas o ciclo fica lento.

Para acelerar (10-20x), mova o projeto para o filesystem nativo do WSL:

```bash
cp -r /mnt/c/Projetos/EstudoPessoal/CorrigeAI ~/CorrigeAI
cd ~/CorrigeAI && docker compose up -d
```

O acesso pelo Windows passa a ser pelo caminho de rede do WSL.
