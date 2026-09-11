FROM python:3.12-slim

# OpenCV precisa dessas libs de sistema mesmo na versão headless.
# libglib2.0-0 e libgomp1 não vêm na imagem slim e o import quebra sem elas.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements copiado antes do código: o Docker cacheia a camada de deps
# e não reinstala tudo a cada alteração no main.py.
COPY ocr-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr-service/ .

# --reload: hot reload em dev. Tirar em produção.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
