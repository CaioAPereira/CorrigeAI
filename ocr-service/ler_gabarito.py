"""
CorrigeAI — leitor de gabarito via linha de comando.

Script único e autocontido (não depende de outros arquivos do projeto):
copie só este arquivo para qualquer PC com Python 3.10+ e as dependências
abaixo instaladas, e rode. Não depende de Docker, FastAPI, Laravel nem do
restante do projeto — é a via alternativa para quando só o script isolado
é pedido (ex.: entrega do trabalho da faculdade).

Dependências (instalar antes de rodar):
    pip install opencv-python-headless numpy

Uso:
    python ler_gabarito.py caminho/para/imagem.png

O script pergunta, questão por questão, qual é a alternativa correta
(guardada só em memória, nesta execução) e depois lê a imagem para
comparar e mostrar o resultado.
"""
import argparse
import sys

import cv2
import numpy as np

QUESTIONS_COUNT = 8
OPTIONS_COUNT = 4
OPTION_LETTERS = ["A", "B", "C", "D"]

# Fração da altura/largura da célula usada como margem ao medir o quanto
# está escura — evita contar as bordas da própria caixa impressa como marcação.
CELL_INSET_RATIO = 0.15

# Diferença mínima (em proporção de pixels escuros) entre a célula mais escura
# e a segunda mais escura da linha para considerar a resposta como marcada.
MIN_DARKNESS_MARGIN = 0.08


class OmrError(Exception):
    """Erro de leitura do gabarito (grade não localizada, imagem inválida etc.)."""


def read_answers_from_bytes(contents: bytes) -> dict[str, str | None]:
    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

    if image is None:
        raise OmrError("Não foi possível decodificar a imagem enviada.")

    grid = _extract_grid(image)
    return _read_answers(grid)


def _extract_grid(image: np.ndarray) -> np.ndarray:
    """Localiza o maior contorno retangular da imagem (a borda da grade de
    respostas) e devolve a imagem já corrigida de perspectiva, contendo
    somente essa grade."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise OmrError("Não foi possível localizar a grade de respostas na imagem.")

    largest = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * perimeter, True)

    if len(approx) != 4:
        raise OmrError("Não foi possível identificar os 4 cantos da grade de respostas.")

    corners = _order_corners(approx.reshape(4, 2).astype(np.float32))
    width, height = _target_size(corners)

    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    warped = cv2.warpPerspective(gray, matrix, (width, height))

    return warped


def _order_corners(points: np.ndarray) -> np.ndarray:
    """Ordena 4 pontos como [topo-esquerda, topo-direita, baixo-direita, baixo-esquerda]."""
    ordered = np.zeros((4, 2), dtype=np.float32)

    sums = points.sum(axis=1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]

    diffs = np.diff(points, axis=1)
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]

    return ordered


def _target_size(corners: np.ndarray) -> tuple[int, int]:
    (top_left, top_right, bottom_right, bottom_left) = corners

    width = max(
        int(np.linalg.norm(top_right - top_left)),
        int(np.linalg.norm(bottom_right - bottom_left)),
    )
    height = max(
        int(np.linalg.norm(bottom_left - top_left)),
        int(np.linalg.norm(bottom_right - top_right)),
    )

    return width, height


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


def ask_correct_answers() -> dict[str, str]:
    print(f"Informe a alternativa correta de cada questão ({'/'.join(OPTION_LETTERS)}):")

    correct_answers: dict[str, str] = {}
    for question_number in range(1, QUESTIONS_COUNT + 1):
        while True:
            answer = input(f"Questão {question_number}: ").strip().upper()
            if answer in OPTION_LETTERS:
                correct_answers[str(question_number)] = answer
                break
            print(f"Opção inválida. Digite uma entre {', '.join(OPTION_LETTERS)}.")

    return correct_answers


def main() -> int:
    parser = argparse.ArgumentParser(description="Lê um gabarito a partir de uma imagem e conta os acertos.")
    parser.add_argument("imagem", help="Caminho para o arquivo de imagem do gabarito preenchido.")
    args = parser.parse_args()

    correct_answers = ask_correct_answers()

    with open(args.imagem, "rb") as file:
        contents = file.read()

    try:
        marked_answers = read_answers_from_bytes(contents)
    except OmrError as e:
        print(f"Erro ao ler o gabarito: {e}", file=sys.stderr)
        return 1

    correct_count = 0

    print()
    print(f"{'Questão':<10}{'Marcada':<10}{'Correta':<10}{'Resultado'}")
    for question_number, correct_option in correct_answers.items():
        marked_option = marked_answers.get(question_number)
        is_correct = marked_option == correct_option
        correct_count += is_correct

        marked_display = marked_option or "-"
        result = "OK" if is_correct else "ERRADA"
        print(f"{question_number:<10}{marked_display:<10}{correct_option:<10}{result}")

    print()
    print(f"Total de acertos: {correct_count}/{len(correct_answers)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
