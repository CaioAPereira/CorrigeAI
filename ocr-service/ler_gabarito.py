"""
CorrigeAI — leitor de gabarito via linha de comando.

Script único e autocontido (não depende de outros arquivos do projeto):
copie só este arquivo para qualquer PC com Python 3.10+ e as dependências
abaixo instaladas, e rode. Não depende de Docker, FastAPI, Laravel nem do
restante do projeto — é a via alternativa para quando só o script isolado
é pedido (ex.: entrega do trabalho da faculdade).

Dependências (instalar antes de rodar):
    pip install opencv-python-headless numpy

    Opcional, para ler também Nome/CPF/RG do cabeçalho:
        pip install pytesseract
        e o binário do Tesseract (Linux: apt install tesseract-ocr tesseract-ocr-por;
        Windows: instalador do UB-Mannheim). Sem isso o script ainda corrige
        as respostas normalmente, só não identifica o aluno.

Uso:
    python ler_gabarito.py                      (modo interativo)
    python ler_gabarito.py caminho/imagem.png   (direto, formato padrão 8x4)
    python ler_gabarito.py foto.png -q 10 -o 5  (direto, outro formato)

No modo interativo o script pergunta o formato da prova (quantas questões
e quantas alternativas), o gabarito, e então o caminho da imagem. Depois de
mostrar o resultado, oferece ler outra imagem reaproveitando o mesmo
gabarito — assim dá para conferir a turma inteira digitando o gabarito
uma única vez.

Tudo fica em memória: o script não grava nada em disco nem usa banco.
"""
import argparse
import os
import re
import sys

import cv2
import numpy as np

# Formato padrão da folha. Deixa de ser fixo: o formato real circula por
# parâmetro em toda a cadeia de leitura, porque a quantidade de caixinhas é
# usada até para ESCOLHER qual retângulo da imagem é a grade de respostas.
DEFAULT_QUESTIONS_COUNT = 8
DEFAULT_OPTIONS_COUNT = 4

MAX_QUESTIONS_COUNT = 60
MAX_OPTIONS_COUNT = 5

ALPHABET = "ABCDE"


def option_letters(options_count: int) -> list[str]:
    """Letras válidas para um formato: 4 alternativas -> A, B, C, D."""
    return list(ALPHABET[:options_count])

# Fração da altura/largura da célula usada como margem ao medir o quanto
# está escura — evita contar as bordas da própria caixa impressa como marcação.
CELL_INSET_RATIO = 0.15

# Diferença mínima (em proporção de pixels escuros) entre a célula mais escura
# e a segunda mais escura da linha para considerar a resposta como marcada.
MIN_DARKNESS_MARGIN = 0.08

# Faixa de área (em fração da imagem) que um contorno precisa ter para ser
# considerado um campo do formulário: descarta ruído e a moldura externa.
MIN_AREA_RATIO = 0.01
MAX_AREA_RATIO = 0.60
POLY_EPSILON_RATIO = 0.02

# Preparo do recorte antes do OCR de texto.
TARGET_HEIGHT = 96
FIELD_INSET_Y_RATIO = 0.10
FIELD_INSET_X_RATIO = 0.01

CPF_DIGITS = 11
RG_DIGITS = 9


class OmrError(Exception):
    """Erro de leitura do gabarito (grade não localizada, imagem inválida etc.)."""


def read_sheet_from_bytes(
    contents: bytes,
    questions_count: int = DEFAULT_QUESTIONS_COUNT,
    options_count: int = DEFAULT_OPTIONS_COUNT,
) -> dict:
    """Lê a folha inteira: cabeçalho (aluno) + respostas."""
    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

    if image is None:
        raise OmrError("Não foi possível decodificar a imagem enviada.")

    regions = _find_regions(image, questions_count, options_count)

    return {
        "student": _read_student(regions),
        "answers": _read_answers(regions["grid"], questions_count, options_count),
    }


def _find_regions(image: np.ndarray, questions_count: int, options_count: int) -> dict[str, np.ndarray]:
    """Localiza os campos Nome/CPF/RG e a grade de respostas na imagem."""
    candidates = _find_rectangles(image)

    if not candidates:
        raise OmrError("Não foi possível localizar a grade de respostas na imagem.")

    grid = _pick_grid(candidates, questions_count, options_count)
    regions = {"grid": grid[0]}

    _, grid_corners = grid
    grid_top = grid_corners[0][1]

    above = [
        (warped, corners) for warped, corners in candidates
        if corners is not grid_corners and corners.mean(axis=0)[1] < grid_top
    ]

    if above:
        by_height = sorted(above, key=lambda item: item[1].mean(axis=0)[1])
        regions["name"] = by_height[0][0]

        second_row = sorted(by_height[1:], key=lambda item: item[1].mean(axis=0)[0])
        if len(second_row) >= 1:
            regions["cpf"] = second_row[0][0]
        if len(second_row) >= 2:
            regions["rg"] = second_row[1][0]

    return regions


def _find_rectangles(image: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    image_area = float(image.shape[0] * image.shape[1])
    found: list[tuple[np.ndarray, np.ndarray]] = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < image_area * MIN_AREA_RATIO or area > image_area * MAX_AREA_RATIO:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, POLY_EPSILON_RATIO * perimeter, True)

        if len(approx) != 4:
            continue

        corners = _order_corners(approx.reshape(4, 2).astype(np.float32))
        found.append((_warp(gray, corners), corners))

    return _deduplicate(found)


def _deduplicate(regions: list[tuple[np.ndarray, np.ndarray]]) -> list[tuple[np.ndarray, np.ndarray]]:
    """Descarta contornos coincidentes (interno/externo da mesma borda)."""
    kept: list[tuple[np.ndarray, np.ndarray]] = []

    for warped, corners in sorted(regions, key=lambda item: -cv2.contourArea(item[1])):
        area = cv2.contourArea(corners)
        center_x, center_y = corners.mean(axis=0)
        side = np.sqrt(area)

        is_duplicate = False
        for _, kept_corners in kept:
            kept_x, kept_y = kept_corners.mean(axis=0)
            kept_area = cv2.contourArea(kept_corners)

            if (
                abs(center_x - kept_x) < side * 0.05
                and abs(center_y - kept_y) < side * 0.05
                and abs(area - kept_area) < kept_area * 0.25
            ):
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append((warped, corners))

    return kept


def _pick_grid(
    candidates: list[tuple[np.ndarray, np.ndarray]],
    questions_count: int,
    options_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """A grade é o retângulo cuja contagem de caixinhas bate com o formato
    informado — não o maior deles.

    No modelo do gabarito a grade fica dentro do bloco "Respostas:", que é
    maior e igualmente retangular; por isso a escolha é pelo conteúdo. É
    também por isso que o formato precisa chegar até aqui: informar 10x5
    quando a folha é 8x4 pode fazer o script eleger o retângulo errado.
    """
    expected_cells = questions_count * options_count

    scored = [
        (abs(_count_cells(warped) - expected_cells),
         cv2.contourArea(corners), warped, corners)
        for warped, corners in candidates
    ]

    best_error = min(item[0] for item in scored)
    best = min((item for item in scored if item[0] == best_error), key=lambda item: item[1])

    return best[2], best[3]


def _count_cells(region: np.ndarray) -> int:
    _, thresh = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    area = float(region.shape[0] * region.shape[1])
    seen: list[tuple[float, float]] = []

    for contour in contours:
        contour_area = cv2.contourArea(contour)

        if not (area * 0.004 < contour_area < area * 0.06):
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, POLY_EPSILON_RATIO * perimeter, True)

        if len(approx) != 4:
            continue

        x, y = approx.reshape(-1, 2).mean(axis=0)
        side = np.sqrt(contour_area)

        if any(abs(x - sx) < side * 0.5 and abs(y - sy) < side * 0.5 for sx, sy in seen):
            continue

        seen.append((float(x), float(y)))

    return len(seen)


def _warp(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    width, height = _target_size(corners)

    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)

    return cv2.warpPerspective(gray, matrix, (width, height))


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

    return max(width, 1), max(height, 1)


def _read_student(regions: dict[str, np.ndarray]) -> dict[str, str | None]:
    """Lê Nome/CPF/RG. Devolve vazio se o Tesseract não estiver disponível."""
    student: dict[str, str | None] = {}

    if "name" in regions:
        student["name"] = _read_text(regions["name"], digits_only=False)

    for field, expected in (("cpf", CPF_DIGITS), ("rg", RG_DIGITS)):
        if field in regions:
            text = _read_text(regions[field], digits_only=True)
            student[field] = re.sub(r"[^0-9./-]", "", text or "").strip("./-") or None

    return student


def _read_text(field: np.ndarray, digits_only: bool) -> str | None:
    try:
        import pytesseract
    except ImportError:
        return None

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
    prepared = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    config = "--psm 7"
    if digits_only:
        config += " -c tessedit_char_whitelist=0123456789.-/"

    try:
        text = pytesseract.image_to_string(prepared, lang="por", config=config)
    except Exception:
        return None

    return text.strip() or None


def _read_answers(grid: np.ndarray, questions_count: int, options_count: int) -> dict[str, str | None]:
    """Devolve a alternativa marcada de cada questão, com a margem de
    confiança da decisão — é a margem que diz onde calibrar o threshold."""
    _, thresh = cv2.threshold(grid, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    height, width = thresh.shape
    cell_height = height / questions_count
    cell_width = width / options_count

    letters = option_letters(options_count)
    answers: dict[str, str | None] = {}

    for row in range(questions_count):
        darkness_by_option = [
            _cell_darkness(thresh, row, col, cell_height, cell_width)
            for col in range(options_count)
        ]

        answers[str(row + 1)] = _pick_marked_option(darkness_by_option, letters)

    return answers


def _answer_margins(grid: np.ndarray, questions_count: int, options_count: int) -> dict[str, float]:
    """Margem (diferença entre a célula mais escura e a segunda) por questão.

    Margem baixa significa decisão apertada: é onde o OMR erra primeiro
    quando a folha é preenchida à mão com caneta fina ou luz irregular.
    """
    _, thresh = cv2.threshold(grid, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    height, width = thresh.shape
    cell_height = height / questions_count
    cell_width = width / options_count

    margins: dict[str, float] = {}

    for row in range(questions_count):
        darkness = sorted(
            (
                _cell_darkness(thresh, row, col, cell_height, cell_width)
                for col in range(options_count)
            ),
            reverse=True,
        )
        margins[str(row + 1)] = darkness[0] - darkness[1]

    return margins


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


def _pick_marked_option(darkness_by_option: list[float], letters: list[str]) -> str | None:
    sorted_darkness = sorted(darkness_by_option, reverse=True)
    darkest = sorted_darkness[0]
    second_darkest = sorted_darkness[1]

    if darkest - second_darkest < MIN_DARKNESS_MARGIN:
        return None

    return letters[darkness_by_option.index(darkest)]


def ask_int(prompt: str, default: int, minimum: int, maximum: int) -> int:
    """Pergunta um número inteiro com valor padrão (Enter aceita o padrão)."""
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()

        if raw == "":
            return default

        try:
            value = int(raw)
        except ValueError:
            print("  Digite um número.")
            continue

        if not minimum <= value <= maximum:
            print(f"  Informe um valor entre {minimum} e {maximum}.")
            continue

        return value


def ask_correct_answers(questions_count: int, letters: list[str]) -> dict[str, str]:
    """Pergunta o gabarito questão por questão. Fica só em memória."""
    print()
    print(f"Gabarito — informe a alternativa correta ({'/'.join(letters)}).")
    print("Deixe em branco e tecle Enter para marcar a questão como anulada.")

    correct_answers: dict[str, str] = {}

    for question_number in range(1, questions_count + 1):
        while True:
            answer = input(f"  Questão {question_number}: ").strip().upper()

            if answer == "":
                correct_answers[str(question_number)] = ""
                break

            if answer in letters:
                correct_answers[str(question_number)] = answer
                break

            print(f"    Opção inválida. Digite uma entre {', '.join(letters)}.")

    return correct_answers


def ask_image_path() -> str | None:
    """Pede o caminho da imagem. Vazio encerra.

    Aceita caminho arrastado para o terminal, que costuma vir com aspas ou
    com espaços escapados.
    """
    while True:
        raw = input("Caminho da imagem (Enter para sair): ").strip()

        if raw == "":
            return None

        path = raw.strip('"').strip("'").replace("\\ ", " ")

        if os.path.isfile(path):
            return path

        print(f"  Arquivo não encontrado: {path}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "S/n" if default else "s/N"

    while True:
        raw = input(f"{prompt} [{suffix}]: ").strip().lower()

        if raw == "":
            return default
        if raw in ("s", "sim", "y", "yes"):
            return True
        if raw in ("n", "nao", "não", "no"):
            return False

        print("  Responda s ou n.")


def process_image(
    path: str,
    correct_answers: dict[str, str],
    questions_count: int,
    options_count: int,
) -> bool:
    """Lê uma imagem e imprime o panorama. Devolve False se a leitura falhou."""
    with open(path, "rb") as file:
        contents = file.read()

    try:
        sheet = read_sheet_from_bytes(contents, questions_count, options_count)
    except OmrError as e:
        print(f"Erro ao ler o gabarito: {e}", file=sys.stderr)
        return False

    # A margem é recalculada à parte para não alterar o formato de retorno de
    # read_sheet_from_bytes, que espelha o do serviço HTTP.
    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    margins: dict[str, float] = {}
    detected_cells = None

    try:
        grid = _find_regions(image, questions_count, options_count)["grid"]
        margins = _answer_margins(grid, questions_count, options_count)
        detected_cells = _count_cells(grid)
    except OmrError:
        pass

    print_report(
        sheet, correct_answers, margins, os.path.basename(path),
        questions_count, options_count, detected_cells,
    )

    return True


def print_report(
    sheet: dict,
    correct_answers: dict[str, str],
    margins: dict[str, float],
    filename: str,
    questions_count: int,
    options_count: int,
    detected_cells: int | None = None,
) -> None:
    student = sheet["student"]
    marked_answers = sheet["answers"]

    print()
    print("=" * 62)
    print(f"Folha: {filename}")
    print("=" * 62)

    # Informar um formato que não é o da folha faz o script fatiar a mesma
    # grade em células imaginárias e produzir uma nota plausível porém falsa.
    # Melhor gritar aqui do que deixar você calibrar em cima de um número errado.
    expected_cells = questions_count * options_count
    if detected_cells is not None and abs(detected_cells - expected_cells) > max(2, expected_cells * 0.1):
        print()
        print(f"!! ATENÇÃO: você informou {questions_count}x{options_count} "
              f"({expected_cells} caixinhas), mas a folha aparenta ter {detected_cells}.")
        print("!! O resultado abaixo provavelmente está errado. Confira o formato da prova.")
        print()

    if student:
        print("Aluno identificado na folha:")
        print(f"  Nome: {student.get('name') or '(não lido)'}")
        print(f"  CPF:  {student.get('cpf') or '(não lido)'}")
        print(f"  RG:   {student.get('rg') or '(não lido)'}")
    else:
        print("Cabeçalho não lido (Tesseract não instalado ou campos não localizados).")

    print()
    print(f"{'Questão':<9}{'Marcada':<9}{'Correta':<9}{'Margem':<9}{'Resultado'}")
    print("-" * 62)

    correct_count = 0
    blank_count = 0
    tight_count = 0
    scored_count = 0

    for question_number in sorted(correct_answers, key=int):
        correct_option = correct_answers[question_number]
        marked_option = marked_answers.get(question_number)
        margin = margins.get(question_number)

        if marked_option is None:
            blank_count += 1

        # Questão anulada (gabarito em branco) não entra no total.
        if correct_option == "":
            result = "ANULADA"
        else:
            scored_count += 1
            is_correct = marked_option == correct_option
            correct_count += is_correct
            result = "OK" if is_correct else "ERRADA"

        # Uma decisão perto do limite acerta hoje e erra amanhã com outra luz.
        margin_display = "-"
        if margin is not None:
            margin_display = f"{margin:.3f}"
            if margin < MIN_DARKNESS_MARGIN * 1.5:
                tight_count += 1
                margin_display += "!"

        print(
            f"{question_number:<9}{marked_option or '-':<9}"
            f"{correct_option or '-':<9}{margin_display:<9}{result}"
        )

    print("-" * 62)

    if scored_count:
        percent = correct_count / scored_count * 100
        print(f"Acertos: {correct_count}/{scored_count}  ({percent:.1f}%)")
    else:
        print("Nenhuma questão valendo nota.")

    if blank_count:
        print(f"Em branco / não detectadas: {blank_count}")

    if tight_count:
        print(
            f"Atenção: {tight_count} questão(ões) com margem apertada (marcadas com !). "
            f"Limite atual: {MIN_DARKNESS_MARGIN:.3f}."
        )
        print("Se alguma delas veio errada, é aqui que se calibra MIN_DARKNESS_MARGIN.")

    print()


def run_interactive() -> int:
    print("CorrigeAI — leitor de gabarito")
    print("-" * 62)
    print("Formato da folha:")

    questions_count = ask_int("  Quantas questões", DEFAULT_QUESTIONS_COUNT, 1, MAX_QUESTIONS_COUNT)
    options_count = ask_int("  Quantas alternativas por questão", DEFAULT_OPTIONS_COUNT, 2, MAX_OPTIONS_COUNT)

    letters = option_letters(options_count)
    correct_answers = ask_correct_answers(questions_count, letters)

    processed = 0

    while True:
        print()
        path = ask_image_path()

        if path is None:
            break

        if process_image(path, correct_answers, questions_count, options_count):
            processed += 1

        if not ask_yes_no("Ler outra folha com o mesmo gabarito?"):
            break

    print(f"Folhas lidas nesta sessão: {processed}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lê um gabarito a partir de uma imagem e conta os acertos.",
    )
    parser.add_argument(
        "imagem",
        nargs="?",
        help="Caminho da imagem. Omitido, o script entra em modo interativo.",
    )
    parser.add_argument(
        "-q", "--questoes", type=int, default=DEFAULT_QUESTIONS_COUNT,
        help=f"Quantidade de questões (padrão: {DEFAULT_QUESTIONS_COUNT}).",
    )
    parser.add_argument(
        "-o", "--opcoes", type=int, default=DEFAULT_OPTIONS_COUNT,
        help=f"Alternativas por questão (padrão: {DEFAULT_OPTIONS_COUNT}).",
    )
    args = parser.parse_args()

    if args.imagem is None:
        return run_interactive()

    if not 1 <= args.questoes <= MAX_QUESTIONS_COUNT:
        print(f"Quantidade de questões inválida (1 a {MAX_QUESTIONS_COUNT}).", file=sys.stderr)
        return 1

    if not 2 <= args.opcoes <= MAX_OPTIONS_COUNT:
        print(f"Alternativas por questão inválidas (2 a {MAX_OPTIONS_COUNT}).", file=sys.stderr)
        return 1

    if not os.path.isfile(args.imagem):
        print(f"Arquivo não encontrado: {args.imagem}", file=sys.stderr)
        return 1

    letters = option_letters(args.opcoes)
    correct_answers = ask_correct_answers(args.questoes, letters)

    return 0 if process_image(args.imagem, correct_answers, args.questoes, args.opcoes) else 1


if __name__ == "__main__":
    sys.exit(main())
