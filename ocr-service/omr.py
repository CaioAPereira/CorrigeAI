"""
CorrigeAI — leitura do gabarito.

Junta as duas metades do problema: a grade de respostas (OMR — célula escura
ou não) e os campos de texto do cabeçalho (Nome, CPF, RG — OCR de verdade,
ver text_reader.py). A localização das regiões na foto fica em layout.py.
"""
import cv2
import numpy as np

import layout
import text_reader

QUESTIONS_COUNT = 8
OPTIONS_COUNT = 4
OPTION_LETTERS = ["A", "B", "C", "D"]

# Fração do lado da caixinha descartada em cada borda antes de medir a tinta.
# A caixinha aqui é a DETECTADA na imagem, não uma fatia geométrica da grade,
# então essa margem só precisa cobrir a espessura da linha impressa.
CELL_INSET_RATIO = 0.12

# Proporção mínima de tinta dentro da caixinha para considerá-la marcada.
# Medindo dentro da caixa real, célula vazia dá ~0.000; um "X" de duas riscas
# finas dá ~0.06-0.13 e um quadrado totalmente pintado dá ~0.99. O limiar fica
# baixo de propósito: o que separa marcada de vazia é a ausência de tinta, não
# a quantidade dela. Um limiar alto (o antigo 0.08 sobre a fatia geométrica)
# só reconhecia o preenchimento total e descartava todo "X".
MIN_INK_RATIO = 0.03

# Quanto a marca mais forte precisa superar a segunda para não ser ambígua.
# Margem ABSOLUTA, que resolve o caso comum: uma alternativa marcada contra
# três vazias (que dão ~0.000).
MIN_INK_MARGIN = 0.02

# Acima desta proporção de tinta a caixinha é considerada deliberadamente
# marcada, não sujeira nem encosto de traço vizinho.
CLEARLY_MARKED_INK = 0.30

# Margem RELATIVA, para quando duas caixinhas estão as duas marcadas. A margem
# absoluta sozinha não cobre esse caso: numa folha com B=0.784 e C=0.835 (as
# duas totalmente pintadas pelo aluno) a diferença de 0.05 supera o piso de
# 0.02 e a leitura seria entregue como "C", escolhendo por ruído de quanto a
# caneta cobriu cada quadrado. Numa prova, duas alternativas marcadas é
# questão anulada, não a mais escura: exigindo que a vencedora tenha ao menos
# o dobro da tinta da segunda, esse par cai em None e vai para a conferência
# do professor, que é onde a decisão deve ser tomada.
AMBIGUOUS_INK_RATIO = 0.50

# Parâmetros do plano B (fatiamento geométrico da grade), onde a borda
# impressa entra na medição e por isso o limiar precisa ser bem mais alto.
FALLBACK_INSET_RATIO = 0.15
FALLBACK_DARKNESS_MARGIN = 0.08

# Quantidade de dígitos esperada em cada documento, usada só para avaliar se a
# leitura é plausível. O CPF é fixo em 11. O RG varia por estado e o dígito
# verificador pode ou não estar presente: em SP, "38.312.468-2" tem 10. Por
# isso o RG é uma FAIXA, não um número — fixá-lo em 9 fazia uma leitura
# truncada ("38.312.468", exatamente 9 dígitos) pontuar como acerto perfeito
# e vencer a leitura correta de 10, entregando um RG errado sem pedir revisão.
CPF_DIGITS = (11, 11)
RG_DIGITS = (8, 10)


class OmrError(Exception):
    """Erro de leitura do gabarito (grade não localizada, imagem inválida etc.)."""


def read_sheet_from_bytes(contents: bytes) -> dict:
    """Lê a folha inteira: cabeçalho (aluno) + respostas."""
    try:
        image = layout.decode_image(contents)
        regions = layout.find_regions(image)
    except layout.LayoutError as e:
        raise OmrError(str(e)) from e

    return {
        "student": _read_student(regions),
        "answers": _read_answers(regions["grid"].image),
    }


def read_answers_from_bytes(contents: bytes) -> dict[str, str | None]:
    """Compatibilidade: só as respostas, no formato antigo."""
    return read_sheet_from_bytes(contents)["answers"]


def _read_student(regions: dict[str, layout.Region]) -> dict:
    """Lê Nome, CPF e RG das regiões do cabeçalho que foram localizadas."""
    student: dict = {}

    if "name" in regions:
        student["name"] = text_reader.read_name(regions["name"].image).to_dict()

    for field, expected_digits in (("cpf", CPF_DIGITS), ("rg", RG_DIGITS)):
        if field in regions:
            student[field] = text_reader.read_document_number(
                regions[field].image, expected_digits
            ).to_dict()

    return student


def _read_answers(grid: np.ndarray) -> dict[str, str | None]:
    """Lê a grade medindo a tinta dentro de cada caixinha.

    A medição é feita na caixinha DETECTADA, não numa fatia geométrica da
    grade. Fatiar a grade em 8x4 e contar pixels escuros inclui a borda
    impressa da caixa no denominador: ela sozinha já responde por ~12% de
    pixels escuros, enquanto as duas riscas finas de um "X" acrescentam só
    ~5%. Assim, marcar com "X" ficava indistinguível de célula vazia — só
    quadrado inteiramente pintado passava. Recortando por dentro da borda,
    célula vazia zera e qualquer traço do aluno aparece.
    """
    _, thresh = cv2.threshold(grid, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    cells = _detect_cells(thresh)

    if cells is None:
        return _read_answers_by_slicing(thresh)

    answers: dict[str, str | None] = {}

    for row, row_cells in enumerate(cells):
        ink_by_option = [_cell_ink(thresh, box) for box in row_cells]
        answers[str(row + 1)] = _pick_marked_option(ink_by_option)

    return answers


def _detect_cells(thresh: np.ndarray) -> list[list[tuple[int, int, int, int]]] | None:
    """Acha as 32 caixinhas e as organiza em 8 linhas de 4.

    Devolve None se não achar exatamente 32 — aí o chamador volta para o
    fatiamento geométrico, que é menos preciso mas não depende de a foto ter
    todas as bordas nítidas.
    """
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    area = float(thresh.shape[0] * thresh.shape[1])
    boxes: list[tuple[int, int, int, int]] = []

    for contour in contours:
        contour_area = cv2.contourArea(contour)

        if not (area * 0.004 < contour_area < area * 0.06):
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        if len(approx) != 4:
            continue

        boxes.append(cv2.boundingRect(approx))

    # A borda tem espessura e gera contorno por fora e por dentro. Aqui fica o
    # MENOR de cada par (o lado de dentro), que é justamente o que queremos
    # medir: o miolo da caixa, já sem a linha impressa.
    boxes.sort(key=lambda box: box[2] * box[3])
    kept: list[tuple[int, int, int, int]] = []

    for x, y, w, h in boxes:
        center_x, center_y = x + w / 2, y + h / 2

        if any(
            abs(center_x - (kx + kw / 2)) < kw * 0.5
            and abs(center_y - (ky + kh / 2)) < kh * 0.5
            for kx, ky, kw, kh in kept
        ):
            continue

        kept.append((x, y, w, h))

    if len(kept) != QUESTIONS_COUNT * OPTIONS_COUNT:
        return None

    kept.sort(key=lambda box: box[1])

    return [
        sorted(kept[row * OPTIONS_COUNT:(row + 1) * OPTIONS_COUNT], key=lambda box: box[0])
        for row in range(QUESTIONS_COUNT)
    ]


def _cell_ink(thresh: np.ndarray, box: tuple[int, int, int, int]) -> float:
    x, y, width, height = box

    inset_x = int(width * CELL_INSET_RATIO)
    inset_y = int(height * CELL_INSET_RATIO)

    cell = thresh[y + inset_y:y + height - inset_y, x + inset_x:x + width - inset_x]

    if cell.size == 0:
        return 0.0

    return float(np.count_nonzero(cell)) / float(cell.size)


def _read_answers_by_slicing(thresh: np.ndarray) -> dict[str, str | None]:
    """Plano B: divide a grade em 8x4 iguais quando as caixas não foram achadas.

    Aqui a borda impressa entra na conta, então a margem exigida precisa ser
    bem maior — este caminho reconhece preenchimento forte, não "X" leve.
    """
    height, width = thresh.shape
    cell_height = height / QUESTIONS_COUNT
    cell_width = width / OPTIONS_COUNT

    answers: dict[str, str | None] = {}

    for row in range(QUESTIONS_COUNT):
        darkness_by_option = [
            _cell_darkness(thresh, row, col, cell_height, cell_width)
            for col in range(OPTIONS_COUNT)
        ]
        sorted_darkness = sorted(darkness_by_option, reverse=True)

        if sorted_darkness[0] - sorted_darkness[1] < FALLBACK_DARKNESS_MARGIN:
            answers[str(row + 1)] = None
        else:
            answers[str(row + 1)] = OPTION_LETTERS[
                darkness_by_option.index(sorted_darkness[0])
            ]

    return answers


def _cell_darkness(thresh: np.ndarray, row: int, col: int, cell_height: float, cell_width: float) -> float:
    y_start = int(row * cell_height)
    y_end = int((row + 1) * cell_height)
    x_start = int(col * cell_width)
    x_end = int((col + 1) * cell_width)

    inset_y = int((y_end - y_start) * FALLBACK_INSET_RATIO)
    inset_x = int((x_end - x_start) * FALLBACK_INSET_RATIO)

    cell = thresh[y_start + inset_y:y_end - inset_y, x_start + inset_x:x_end - inset_x]
    if cell.size == 0:
        return 0.0

    return float(np.count_nonzero(cell)) / float(cell.size)


def _pick_marked_option(ink_by_option: list[float]) -> str | None:
    """Escolhe a alternativa marcada, ou None se estiver em branco/ambígua."""
    sorted_ink = sorted(ink_by_option, reverse=True)
    strongest, runner_up = sorted_ink[0], sorted_ink[1]

    if strongest < MIN_INK_RATIO:
        return None

    if strongest - runner_up < MIN_INK_MARGIN:
        return None

    # Duas caixinhas claramente marcadas: questão ambígua, não "vale a mais
    # escura". Só se aplica quando a segunda também passou do limiar de marca
    # deliberada, para não penalizar o caso normal (uma marcada, três em ~0).
    if runner_up >= CLEARLY_MARKED_INK and runner_up > strongest * AMBIGUOUS_INK_RATIO:
        return None

    return OPTION_LETTERS[ink_by_option.index(strongest)]
