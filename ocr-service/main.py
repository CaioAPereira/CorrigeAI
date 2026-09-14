"""
CorrigeAI — Serviço de leitura óptica (OMR).

Wrapper HTTP sobre a lógica de leitura em omr.py. Recebe a foto do gabarito
e devolve, por questão, qual alternativa (A-D) foi marcada — ou null se
estiver em branco/ilegível.
"""
from fastapi import FastAPI, File, HTTPException, UploadFile

from omr import OmrError, read_answers_from_bytes

app = FastAPI(title="CorrigeAI OCR Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/read")
async def read(file: UploadFile = File(...)) -> dict[str, str | None]:
    contents = await file.read()

    try:
        return read_answers_from_bytes(contents)
    except OmrError as e:
        raise HTTPException(status_code=422, detail=str(e))
