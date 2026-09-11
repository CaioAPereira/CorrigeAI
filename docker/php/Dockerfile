FROM php:8.4-fpm-alpine

# libpq  -> runtime do driver PostgreSQL
# Os -dev são build-only: instalados, usados para compilar as extensões, e removidos.
RUN apk add --no-cache libpq libzip icu-libs oniguruma \
    && apk add --no-cache --virtual .build-deps \
        postgresql-dev libzip-dev icu-dev oniguruma-dev autoconf g++ make linux-headers \
    # pdo_pgsql: o driver que o Laravel usa com DB_CONNECTION=pgsql
    && docker-php-ext-install -j"$(nproc)" pdo_pgsql pgsql zip intl mbstring bcmath opcache \
    && apk del .build-deps

# Composer: copiado da imagem oficial em vez de instalado via script.
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# UID 1000 para os arquivos criados no container não virarem root no seu host.
RUN adduser -D -u 1000 -g '' appuser \
    && chown -R appuser:appuser /var/www/html
USER appuser

EXPOSE 9000
CMD ["php-fpm"]
