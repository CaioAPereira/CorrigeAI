"""
CorrigeAI — Serviço de leitura óptica (OMR).

Placeholder mínimo só para o container subir e a integração ser testável.
O endpoint real de leitura será implementado na próxima etapa.
"""
from fastapi import FastAPI

app = FastAPI(title="CorrigeAI OCR Service")


@app.get("/health")
def health():
    return {"status": "ok"}
