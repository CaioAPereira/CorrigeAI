"""
CorrigeAI — leitura dos campos de texto do gabarito (Nome, CPF, RG).

Dois motores, porque são dois problemas diferentes:

- Tesseract: rápido, leve, bom em texto impresso e letra de forma regular.
  Usado sempre, e é o único motor para CPF/RG (dígitos, formato previsível).
- TrOCR (modelo de handwriting da Microsoft, via transformers): pesado, mas
  reconhece letra cursiva, onde o Tesseract erra muito. Usado só no Nome,
  em paralelo ao Tesseract; fica a leitura de maior confiança.

O TrOCR é carregado sob demanda (lazy) e cacheado: o serviço sobe rápido e
só paga o custo do modelo na primeira imagem com campo de nome.
"""
import re

import cv2
import numpy as np
import pytesseract

# Altura alvo ao ampliar o recorte do campo antes do OCR. Campos de uma linha
# saem pequenos do warp e ambos os motores erram mais em imagem de baixa
# resolução; ampliar antes de binarizar melhora bastante o acerto.
TARGET_HEIGHT = 96

# Margem removida do recorte para tirar a borda impressa do campo, que o OCR
# leria como caractere. Horizontal bem menor que vertical: a borda tem a mesma
# espessura nos dois sentidos, mas o campo é muito mais largo que alto, e uma
# margem generosa na horizontal come a primeira letra do que foi escrito.
FIELD_INSET_Y_RATIO = 0.10
FIELD_INSET_X_RATIO = 0.01

# Abaixo desta confiança a leitura é devolvida, mas marcada para revisão
# manual pelo professor em vez de ser aceita em silêncio.
LOW_CONFIDENCE_THRESHOLD = 0.60

_TROCR: tuple = ()


class TextResult:
    def __init__(self, text: str, confidence: float, engine: str):
        self.text = text
        self.confidence = confidence
        self.engine = engine

    def to_dict(self) -> dict:
        return {
            "text": self.text or None,
            "confidence": round(self.confidence, 3),
            "engine": self.engine,
            "needs_review": self.confidence < LOW_CONFIDENCE_THRESHOLD or not self.text,
        }


def read_name(field: np.ndarray) -> TextResult:
    """Lê o campo Nome, que pode vir em letra de forma ou manuscrita.

    Roda os dois motores e devolve o de maior confiança, em vez de exigir que
    o professor declare de antemão como o aluno escreveu.
    """
    prepared = _prepare(field)

    results = [_read_with_tesseract(prepared, digits_only=False)]

    handwritten = _read_with_trocr(field)
    if handwritten is not None:
        results.append(handwritten)

    return max(results, key=lambda result: result.confidence)


def read_document_number(field: np.ndarray, expected_digits: int) -> TextResult:
    """Lê CPF ou RG: só dígitos e separadores, sempre via Tesseract.

    O score do Tesseract é pessimista em sequência longa de dígitos — ele não
    tem contexto de dicionário para se apoiar e reporta confiança baixa mesmo
    acertando. Então o formato entra no julgamento: se veio a quantidade certa
    de dígitos, a leitura é plausível e não vira alarme falso de revisão.
    """
    result = _read_with_tesseract(_prepare(field), digits_only=True)
    text = _clean_document(result.text)

    digits = sum(character.isdigit() for character in text)
    confidence = max(result.confidence, 0.75) if digits == expected_digits else result.confidence

    return TextResult(text, confidence, result.engine)


def _prepare(field: np.ndarray) -> np.ndarray:
    """Recorta a borda, amplia e binariza o campo para o OCR."""
    height, width = field.shape[:2]

    inset_y = int(height * FIELD_INSET_Y_RATIO)
    inset_x = int(width * FIELD_INSET_X_RATIO)
    cropped = field[inset_y:height - inset_y, inset_x:width - inset_x]

    if cropped.size == 0:
        cropped = field

    scale = TARGET_HEIGHT / max(cropped.shape[0], 1)
    if scale > 1:
        cropped = cv2.resize(cropped, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    denoised = cv2.bilateralFilter(cropped, 9, 75, 75)

    return cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def _read_with_tesseract(prepared: np.ndarray, digits_only: bool) -> TextResult:
    # --psm 7: trata a imagem como uma única linha de texto, que é exatamente
    # o formato de cada campo do cabeçalho.
    config = "--psm 7"
    if digits_only:
        config += " -c tessedit_char_whitelist=0123456789.-/"

    data = pytesseract.image_to_data(
        prepared,
        lang="por",
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    words: list[str] = []
    confidences: list[float] = []

    for text, confidence in zip(data["text"], data["conf"]):
        text = text.strip()
        confidence = float(confidence)

        if not text or confidence < 0:
            continue

        words.append(text)
        confidences.append(confidence / 100.0)

    if not words:
        return TextResult("", 0.0, "tesseract")

    return TextResult(" ".join(words), float(np.mean(confidences)), "tesseract")


def _read_with_trocr(field: np.ndarray) -> TextResult | None:
    """Lê o campo com o modelo de handwriting. Devolve None se indisponível."""
    loaded = _load_trocr()

    if loaded is None:
        return None

    processor, model, torch = loaded

    rgb = cv2.cvtColor(field, cv2.COLOR_GRAY2RGB)
    pixel_values = processor(images=rgb, return_tensors="pt").pixel_values

    with torch.no_grad():
        generated = model.generate(
            pixel_values,
            max_new_tokens=32,
            output_scores=True,
            return_dict_in_generate=True,
        )

    text = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0].strip()

    # Confiança = média das probabilidades dos tokens efetivamente gerados.
    scores = torch.stack(generated.scores, dim=1).softmax(-1).max(-1).values
    confidence = float(scores.mean()) if scores.numel() else 0.0

    return TextResult(text, confidence, "trocr")


def _load_trocr():
    """Carrega o modelo uma vez por processo. None se transformers/torch faltarem."""
    global _TROCR

    if _TROCR == ():
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            name = "microsoft/trocr-base-handwritten"
            processor = TrOCRProcessor.from_pretrained(name)
            model = VisionEncoderDecoderModel.from_pretrained(name)
            model.eval()

            _TROCR = (processor, model, torch)
        except Exception:
            # Sem o modelo o serviço continua útil: cai para Tesseract sozinho.
            _TROCR = None

    return _TROCR


def _clean_document(text: str) -> str:
    """Normaliza CPF/RG: só dígitos e separadores, sem lixo nas pontas.

    Sobra de borda costuma virar '-' ou '.' no começo/fim da leitura; separador
    só faz sentido entre dígitos.
    """
    return re.sub(r"[^0-9./-]", "", text).strip("./-")
