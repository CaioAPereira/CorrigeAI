"""
CorrigeAI — Serviço de leitura do gabarito.

Wrapper HTTP sobre a lógica em omr.py. Recebe a foto do gabarito e devolve
os dados do aluno lidos no cabeçalho (nome, CPF, RG) e, por questão, qual
alternativa (A-D) foi marcada — ou null se estiver em branco/ilegível.
"""
from fastapi import FastAPI, File, HTTPException, UploadFile

from omr import OmrError, read_sheet_from_bytes

app = FastAPI(title="CorrigeAI OCR Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/read")
async def read(file: UploadFile = File(...)) -> dict:
    contents = await file.read()

    try:
        return read_sheet_from_bytes(contents)
    except OmrError as e:
        raise HTTPException(status_code=422, detail=str(e))
