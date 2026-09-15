FROM python:3.12-slim

# OpenCV precisa dessas libs de sistema mesmo na versão headless.
# libglib2.0-0 e libgomp1 não vêm na imagem slim e o import quebra sem elas.
# tesseract-ocr + o pacote de português são o motor usado no cabeçalho
# (Nome/CPF/RG) — o pytesseract é só um wrapper, não traz o binário.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
        tesseract-ocr \
        tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements copiado antes do código: o Docker cacheia a camada de deps
# e não reinstala tudo a cada alteração no main.py.
COPY ocr-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o modelo de handwriting na build, não na primeira requisição: evita
# a primeira correção travar alguns minutos baixando ~1.3GB.
RUN python -c "from transformers import TrOCRProcessor, VisionEncoderDecoderModel; \
    TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten'); \
    VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')"

COPY ocr-service/ .

# --reload: hot reload em dev. Tirar em produção.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
