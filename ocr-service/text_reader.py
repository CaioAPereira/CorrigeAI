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

# O TrOCR foi treinado em linhas manuscritas isoladas e razoavelmente altas.
# Recebendo uma tira muito baixa — o campo Nome sai do warp com ~30px — ele
# passa a "completar" a linha em vez de transcrevê-la, e inventa um ano no
# fim do nome. Uma altura maior que a do Tesseract compensa isso.
TROCR_TARGET_HEIGHT = 192

# Proporção largura/altura máxima entregue ao TrOCR. O campo sai do warp como
# uma tira de ~35x640 (aspect ~19:1) e o processador do modelo redimensiona
# tudo para 384x384 — uma tira dessas chega ao modelo com a escrita esmagada.
# Acolchoando com o tom do papel até ~6:1, a letra sobrevive ao resize.
TROCR_MAX_ASPECT = 6.0

# Penalidade aplicada à confiança do TrOCR quando foi preciso podar
# alucinação da saída dele: o texto restante pode estar certo, mas o modelo
# já demonstrou que estava completando em vez de ler.
TROCR_HALLUCINATION_PENALTY = 0.25

# O TrOCR reporta média de softmax dos tokens gerados e o Tesseract, média da
# confiança por palavra. São escalas diferentes, e o TrOCR fica *confiante*
# justamente quando alucina, porque inventar um ano é caminho provável no
# modelo de linguagem dele. Comparar os dois números crus faz o TrOCR vencer
# por margem mínima em campo que o Tesseract leu certo, então ele só ganha
# quando abre uma vantagem real sobre o Tesseract.
TROCR_WIN_MARGIN = 0.15

_TROCR: tuple = ()


class TextResult:
    def __init__(self, text: str, confidence: float, engine: str, truncated: bool = False):
        self.text = text
        self.confidence = confidence
        self.engine = engine
        # Leitura que terminou num separador, sinal de que o motor parou antes
        # do último dígito. Não muda o texto, só impede que ele passe como bom.
        self.truncated = truncated

    def to_dict(self) -> dict:
        return {
            "text": self.text or None,
            "confidence": round(self.confidence, 3),
            "engine": self.engine,
            "needs_review": self.confidence < LOW_CONFIDENCE_THRESHOLD or not self.text,
        }


def read_name(field: np.ndarray) -> TextResult:
    """Lê o campo Nome, que pode vir em letra de forma ou manuscrita.

    Roda os dois motores, em vez de exigir que o professor declare de antemão
    como o aluno escreveu. O Tesseract é o padrão e o TrOCR só assume quando
    abre vantagem clara (TROCR_WIN_MARGIN): as confianças dos dois não estão
    na mesma escala, e o TrOCR pontua alto justamente quando alucina.
    """
    printed = _read_with_tesseract(_prepare(field), digits_only=False)
    handwritten = _read_with_trocr(_prepare_for_trocr(field))

    if handwritten is None:
        return printed

    # O Tesseract só é o padrão enquanto o que ele devolve ainda parece um
    # nome. Em cursiva ele produz lixo com pontuação e dígitos ("QU 14) “Abe
    # or O... an.") e, como a confiança dele é média por palavra, esse lixo
    # vencia o TrOCR na comparação numérica.
    if not _looks_like_name(printed.text):
        return handwritten

    if handwritten.confidence > printed.confidence + TROCR_WIN_MARGIN:
        return handwritten

    return printed


def _looks_like_name(text: str) -> bool:
    """Diz se a leitura ainda é plausível como nome de pessoa.

    Não tenta validar o nome — só descartar saída claramente degradada:
    nome de gente não tem dígito, e é feito majoritariamente de letras.
    """
    stripped = text.strip()

    if len(stripped) < 3:
        return False

    if any(character.isdigit() for character in stripped):
        return False

    # Pontuação no meio do texto denuncia leitura degradada: em nome de pessoa
    # só aparecem hífen e apóstrofo ("Anna-Maria", "D'Ávila"). Parêntese,
    # fecha-chave e reticências são lixo do Tesseract tentando ler cursiva.
    if any(character in "()[]{}<>|\\/*#@_=+~^" for character in stripped):
        return False

    letters = sum(character.isalpha() or character.isspace() for character in stripped)

    if letters / len(stripped) < 0.8:
        return False

    # Nome de gente tem palavras; sequência de fragmentos de 1-2 letras é
    # ruído. Exige que a maior parte das palavras tenha tamanho plausível.
    words = stripped.split()
    real_words = sum(len(word) >= 3 for word in words)

    return bool(words) and real_words >= len(words) / 2


def read_document_number(field: np.ndarray, expected_digits: tuple[int, int]) -> TextResult:
    """Lê CPF ou RG, preferindo o motor de manuscrito.

    Na folha real o aluno escreve os documentos à mão, e o Tesseract é um
    motor de texto impresso: em foto de papel ele perde dígitos de forma
    consistente (lia "41161-08" para um CPF que o TrOCR transcreve inteiro).
    Por isso a ordem aqui é o inverso da do Nome — o TrOCR é o padrão, e o
    Tesseract só entra se o TrOCR estiver indisponível ou devolver uma
    contagem de dígitos pior.

    A alucinação que obriga a desconfiar do TrOCR no Nome ([[project-ocr-nome-alucinacao]])
    não tem o mesmo espaço aqui: a saída é validada contra o formato
    esperado, então completar com texto plausível não passa despercebido.
    """
    minimum_digits, maximum_digits = expected_digits

    tesseract = _read_with_tesseract(_prepare(field), digits_only=True)
    candidates = [
        TextResult(
            _clean_document(tesseract.text),
            tesseract.confidence,
            "tesseract",
            _ends_in_separator(tesseract.text),
        )
    ]

    handwritten = _read_with_trocr(_prepare_for_trocr(field))

    if handwritten is not None:
        candidates.insert(
            0,
            TextResult(
                _clean_document(handwritten.text),
                handwritten.confidence,
                "trocr",
                _ends_in_separator(handwritten.text),
            ),
        )

    # Vence quem estiver dentro da faixa de dígitos esperada; fora dela, quem
    # chegar mais perto. Empate fica com o primeiro da lista (o TrOCR, quando
    # ele rodou). Preferir o MAIS LONGO dentro da faixa é de propósito: o erro
    # típico dos dois motores é perder dígito no fim, nunca inventar um.
    best = max(
        candidates,
        key=lambda result: (
            -_digit_distance(result.text, minimum_digits, maximum_digits),
            _digit_count(result.text),
        ),
    )

    digits = _digit_count(best.text)

    # Separador solto no fim ("38.312.468-") é assinatura de leitura cortada:
    # o modelo chegou a ver o separador mas parou antes do dígito seguinte.
    # Sem isso a leitura truncada ainda cai dentro da faixa e é aceita em
    # silêncio — é o pior caso possível, porque um RG errado mas plausível
    # não chama atenção de quem confere.
    if best.truncated:
        return TextResult(best.text, min(best.confidence, 0.4), best.engine)

    plausible = minimum_digits <= digits <= maximum_digits

    if not plausible:
        return TextResult(best.text, min(best.confidence, 0.4), best.engine)

    # O score bruto do Tesseract é pessimista em sequência longa de dígitos
    # (não tem dicionário para se apoiar) e reporta ~0 mesmo acertando, então
    # uma leitura boa cairia em revisão sem necessidade. Mas sustentar a
    # confiança só porque a CONTAGEM de dígitos bate é perigoso: ter 8 dígitos
    # não é ter os 8 dígitos certos. Num RG manuscrito lido como "21369392"
    # (o correto é "394765392") o Tesseract entregava 0.75 — acima do limiar
    # de revisão — e o professor não tinha motivo para desconfiar de um número
    # plausível. É o pior erro possível aqui, porque passa silencioso.
    #
    # O piso então exige corroboração: os dois motores, que erram de formas
    # diferentes, chegarem ao mesmo número é evidência real de acerto. Motor
    # sozinho mantém seu próprio score e, se for baixo, cai em revisão.
    if _corroborated(candidates, best):
        return TextResult(best.text, max(best.confidence, 0.75), best.engine)

    return TextResult(best.text, best.confidence, best.engine)


def _corroborated(candidates: list[TextResult], best: TextResult) -> bool:
    """Diz se outro motor chegou ao mesmo número que o escolhido."""
    return any(
        other is not best and other.text == best.text and other.text
        for other in candidates
    )


def _ends_in_separator(text: str) -> bool:
    """True se a leitura termina em separador, sem dígito depois."""
    return bool(re.search(r"[.\-/]\s*$", text.strip()))


def _digit_count(text: str) -> int:
    return sum(character.isdigit() for character in text)


def _digit_distance(text: str, minimum: int, maximum: int) -> int:
    """Zero se a contagem de dígitos cabe na faixa; senão, o quanto falta/sobra."""
    digits = _digit_count(text)

    if digits < minimum:
        return minimum - digits

    if digits > maximum:
        return digits - maximum

    return 0


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


def _prepare_for_trocr(field: np.ndarray) -> np.ndarray:
    """Recorta a borda e amplia o campo, preservando tom contínuo.

    Não binariza, de propósito: o TrOCR espera imagem natural em escala de
    cinza e perde acurácia com a entrada limiarizada que o Tesseract prefere.
    Mas o inset e a ampliação ele também precisava — antes recebia o recorte
    cru, com a borda impressa junto e a altura original, que é a condição em
    que ele alucina.
    """
    height, width = field.shape[:2]

    inset_y = int(height * FIELD_INSET_Y_RATIO)
    inset_x = int(width * FIELD_INSET_X_RATIO)
    cropped = field[inset_y:height - inset_y, inset_x:width - inset_x]

    if cropped.size == 0:
        cropped = field

    cropped = _pad_to_aspect(cropped, TROCR_MAX_ASPECT)

    scale = TROCR_TARGET_HEIGHT / max(cropped.shape[0], 1)
    if scale > 1:
        cropped = cv2.resize(cropped, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return cropped


def _pad_to_aspect(field: np.ndarray, max_aspect: float) -> np.ndarray:
    """Acolchoa a tira em cima e embaixo até ela caber na proporção alvo.

    O preenchimento usa um tom claro tirado da própria imagem (percentil 90 =
    o papel), e não branco puro, para não criar uma borda artificial de alto
    contraste que o modelo leia como traço.
    """
    height, width = field.shape[:2]

    if height <= 0 or width / height <= max_aspect:
        return field

    target_height = int(width / max_aspect)
    extra = target_height - height
    paper = int(np.percentile(field, 90))

    return cv2.copyMakeBorder(
        field, extra // 2, extra - extra // 2, 0, 0, cv2.BORDER_CONSTANT, value=paper
    )


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

    raw = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0].strip()
    text = _strip_hallucination(raw)

    # Confiança = média das probabilidades dos tokens efetivamente gerados.
    scores = torch.stack(generated.scores, dim=1).softmax(-1).max(-1).values
    confidence = float(scores.mean()) if scores.numel() else 0.0

    if text != raw:
        confidence = max(confidence - TROCR_HALLUCINATION_PENALTY, 0.0)

    return TextResult(text, confidence, "trocr")


def _strip_hallucination(text: str) -> str:
    """Remove da leitura do TrOCR o que ele completou em vez de ler.

    Nome de aluno não termina em ano nem começa com letra solta: os dois
    padrões aparecem de forma sistemática na saída do modelo, inclusive em
    campo que o Tesseract lê sem erro, e não correspondem a nada na imagem.
    """
    cleaned = re.sub(r"[\s,.;:-]*\b\d{4}\s*$", "", text).strip()
    cleaned = re.sub(r"^[^\w]*(?:\b[A-Za-z]\b[\s.,;:-]+)?", "", cleaned).strip()

    return cleaned or text


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
    """Normaliza CPF/RG para **só os dígitos**, sem pontos nem traços.

    Guardar o documento já normalizado é o que permite comparar e futuramente
    casar com um cadastro de aluno: a mesma pessoa pode escrever o RG com ou
    sem pontuação, e o OCR ainda por cima erra o separador com frequência
    (troca '.' por '-' e vice-versa). O dígito é o dado; a máscara é
    apresentação, e fica a cargo de quem exibe.
    """
    return re.sub(r"[^0-9]", "", text)
