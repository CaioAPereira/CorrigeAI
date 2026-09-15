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

# Fração da altura/largura da célula usada como margem ao medir o quanto
# está escura — evita contar as bordas da própria caixa impressa como marcação.
CELL_INSET_RATIO = 0.15

# Diferença mínima (em proporção de pixels escuros) entre a célula mais escura
# e a segunda mais escura da linha para considerar a resposta como marcada.
MIN_DARKNESS_MARGIN = 0.08

# Quantidade de dígitos esperada em cada documento, usada só para avaliar se a
# leitura é plausível. RG varia por estado; 9 é o formato mais comum (SP).
CPF_DIGITS = 11
RG_DIGITS = 9


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
    _, thresh = cv2.threshold(grid, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    height, width = thresh.shape
    cell_height = height / QUESTIONS_COUNT
    cell_width = width / OPTIONS_COUNT

    answers: dict[str, str | None] = {}

    for row in range(QUESTIONS_COUNT):
        darkness_by_option = [
            _cell_darkness(thresh, row, col, cell_height, cell_width)
            for col in range(OPTIONS_COUNT)
        ]

        answers[str(row + 1)] = _pick_marked_option(darkness_by_option)

    return answers


def _cell_darkness(thresh: np.ndarray, row: int, col: int, cell_height: float, cell_width: float) -> float:
    y_start = int(row * cell_height)
    y_end = int((row + 1) * cell_height)
    x_start = int(col * cell_width)
    x_end = int((col + 1) * cell_width)

    inset_y = int((y_end - y_start) * CELL_INSET_RATIO)
    inset_x = int((x_end - x_start) * CELL_INSET_RATIO)

    cell = thresh[y_start + inset_y:y_end - inset_y, x_start + inset_x:x_end - inset_x]
    if cell.size == 0:
        return 0.0

    return float(np.count_nonzero(cell)) / float(cell.size)


def _pick_marked_option(darkness_by_option: list[float]) -> str | None:
    sorted_darkness = sorted(darkness_by_option, reverse=True)
    darkest = sorted_darkness[0]
    second_darkest = sorted_darkness[1]

    if darkest - second_darkest < MIN_DARKNESS_MARGIN:
        return None

    return OPTION_LETTERS[darkness_by_option.index(darkest)]
