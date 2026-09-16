"""
CorrigeAI — localização dos campos do gabarito na imagem.

O modelo do gabarito tem quatro regiões delimitadas por retângulo: os campos
de texto Nome, CPF e RG no topo, e a grade 8x4 de respostas embaixo. Este
módulo acha esses quatro retângulos numa foto e devolve cada região já
recortada e corrigida de perspectiva.

A classificação é geométrica, não depende de cor: a grade é o maior retângulo
da metade inferior; entre os campos de texto do topo, Nome é o que está mais
acima, e CPF/RG são os dois da linha seguinte (CPF à esquerda, RG à direita).
"""
import cv2
import numpy as np

# Um contorno só é considerado campo se ocupar ao menos essa fração da área da
# imagem — descarta ruído, texto solto e as caixinhas individuais da grade.
# Os campos CPF e RG ocupam ~0.6% da foto, então o piso precisa ficar abaixo
# disso: com 0.01 (valor anterior) os dois eram descartados antes da
# classificação e o cabeçalho inteiro vinha vazio.
MIN_AREA_RATIO = 0.004

# E no máximo essa fração — descarta a moldura externa do formulário inteiro,
# que também é um retângulo fechado e engloba todos os campos.
MAX_AREA_RATIO = 0.60

# Tolerância do approxPolyDP ao simplificar o contorno em polígono.
POLY_EPSILON_RATIO = 0.02

# Parâmetros do threshold adaptativo usado para achar os retângulos.
# Em foto de papel a iluminação é desigual (sombra de um lado da folha), e um
# threshold global de Otsu perde as bordas na região mais escura — era por isso
# que o retângulo do campo Nome não era encontrado em foto real.
ADAPTIVE_BLOCK_SIZE = 31
ADAPTIVE_C = 7

# Dimensões da grade de respostas, usadas para reconhecê-la pelo conteúdo.
QUESTIONS_COUNT = 8
OPTIONS_COUNT = 4


class LayoutError(Exception):
    """Não foi possível localizar as regiões esperadas do gabarito."""


class Region:
    """Uma região retangular localizada na imagem, já corrigida de perspectiva."""

    def __init__(self, image: np.ndarray, corners: np.ndarray):
        self.image = image
        self.corners = corners

    @property
    def area(self) -> float:
        return float(cv2.contourArea(self.corners))

    @property
    def center(self) -> tuple[float, float]:
        x, y = self.corners.mean(axis=0)
        return float(x), float(y)


def decode_image(contents: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

    if image is None:
        raise LayoutError("Não foi possível decodificar a imagem enviada.")

    return image


def find_regions(image: np.ndarray) -> dict[str, Region]:
    """Devolve as regiões 'name', 'cpf', 'rg' e 'grid' localizadas na imagem.

    Levanta LayoutError se a grade de respostas não for encontrada. Os campos
    de texto são opcionais: se a foto cortar o cabeçalho, as chaves
    correspondentes simplesmente não vêm no resultado, e o OMR ainda funciona.
    """
    candidates = _find_rectangles(image)

    if not candidates:
        raise LayoutError("Não foi possível localizar a grade de respostas na imagem.")

    grid = _pick_grid(candidates)

    regions = {"grid": grid}
    regions.update(_classify_text_fields(candidates, grid))

    return regions


def _pick_grid(candidates: list[Region]) -> Region:
    """Escolhe qual retângulo é a grade de respostas.

    Não dá para usar "o maior": no modelo a grade fica dentro do bloco
    "Respostas:", que é maior e igualmente retangular. O que distingue a grade
    é o conteúdo — só ela contém as 32 caixinhas (8 linhas x 4 colunas). Então
    contamos quantas caixas cada candidato tem dentro e ficamos com o que mais
    se aproxima de 32; empate desempata pelo menor, que é o recorte mais justo.
    """
    scored = [
        (abs(_count_cells(region.image) - QUESTIONS_COUNT * OPTIONS_COUNT), region.area, region)
        for region in candidates
    ]

    best_error = min(error for error, _, _ in scored)

    return min(
        (item for item in scored if item[0] == best_error),
        key=lambda item: item[1],
    )[2]


def _count_cells(region_image: np.ndarray) -> int:
    """Conta quantas caixinhas (contornos de 4 lados, pequenas) há na região."""
    _, thresh = cv2.threshold(
        region_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    area = float(region_image.shape[0] * region_image.shape[1])
    count = 0
    seen: list[tuple[float, float]] = []

    for contour in contours:
        contour_area = cv2.contourArea(contour)

        # Uma célula da grade 8x4 ocupa ~1/32 da área; a faixa é larga para
        # tolerar a marcação preenchida e variação de enquadramento.
        if not (area * 0.004 < contour_area < area * 0.06):
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, POLY_EPSILON_RATIO * perimeter, True)

        if len(approx) != 4:
            continue

        x, y = approx.reshape(-1, 2).mean(axis=0)
        side = np.sqrt(contour_area)

        # A borda de cada caixinha gera contorno interno e externo: conta uma vez.
        if any(abs(x - sx) < side * 0.5 and abs(y - sy) < side * 0.5 for sx, sy in seen):
            continue

        seen.append((float(x), float(y)))
        count += 1

    return count


def _find_rectangles(image: np.ndarray) -> list[Region]:
    """Acha todo contorno de 4 lados com área plausível para ser um campo."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_BLOCK_SIZE,
        ADAPTIVE_C,
    )

    # RETR_LIST (e não RETR_EXTERNAL): os campos do topo ficam dentro da
    # moldura externa do formulário, então contornos aninhados importam.
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    image_area = float(image.shape[0] * image.shape[1])
    regions: list[Region] = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < image_area * MIN_AREA_RATIO or area > image_area * MAX_AREA_RATIO:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, POLY_EPSILON_RATIO * perimeter, True)

        if len(approx) != 4:
            continue

        corners = _order_corners(approx.reshape(4, 2).astype(np.float32))
        regions.append(Region(_warp(gray, corners), corners))

    return _deduplicate(regions)


def _deduplicate(regions: list[Region]) -> list[Region]:
    """Remove retângulos praticamente coincidentes.

    Uma borda impressa tem espessura, então o threshold costuma gerar dois
    contornos por campo (lado de dentro e lado de fora da linha). Mantém o
    maior de cada par, comparando também o tamanho: no modelo, a grade fica
    dentro do bloco "Respostas", quase concêntrica, e são campos distintos.
    """
    kept: list[Region] = []

    for region in sorted(regions, key=lambda r: r.area, reverse=True):
        center_x, center_y = region.center
        side = np.sqrt(region.area)

        is_duplicate = any(
            abs(center_x - kx) < side * 0.05
            and abs(center_y - ky) < side * 0.05
            and abs(region.area - kept_region.area) < kept_region.area * 0.25
            for (kx, ky), kept_region in (
                (kept_region.center, kept_region) for kept_region in kept
            )
        )

        if not is_duplicate:
            kept.append(region)

    return kept


def _classify_text_fields(candidates: list[Region], grid: Region) -> dict[str, Region]:
    """Identifica Nome, CPF e RG entre os retângulos acima da grade."""
    _, grid_top = grid.corners[0]

    above_grid = [
        region for region in candidates
        if region is not grid and region.center[1] < grid_top
    ]

    if not above_grid:
        return {}

    by_height = sorted(above_grid, key=lambda region: region.center[1])

    # O Nome ocupa a linha inteira; CPF e RG dividem a linha seguinte, então
    # cada um é bem mais estreito. Quando a foto corta o cabeçalho e sobra um
    # único campo, tratá-lo como Nome só porque é o mais alto grava o CPF no
    # campo de nome do aluno, sem qualquer sinal de erro na conferência. Só
    # aceitamos como Nome um campo largo o bastante para ser a linha inteira.
    first = by_height[0]
    rest = by_height[1:]

    if not rest and not _spans_header_row(first, grid):
        # Campo solto e estreito: é um dos documentos, não o Nome. Sem o par
        # ao lado não dá para saber se é CPF ou RG pela posição, e chutar
        # errado é pior do que devolver o cabeçalho vazio — o professor
        # preenche na conferência.
        return {}

    fields = {"name": first}

    # Nome e a dupla CPF/RG estão em linhas distintas; o que sobra abaixo do
    # Nome é a segunda linha, ordenada da esquerda para a direita.
    second_row = sorted(rest, key=lambda region: region.center[0])

    if len(second_row) >= 1:
        fields["cpf"] = second_row[0]
    if len(second_row) >= 2:
        fields["rg"] = second_row[1]

    return fields


def _spans_header_row(region: Region, grid: Region) -> bool:
    """Diz se a região é larga o bastante para ser a linha inteira do Nome.

    A referência é a largura da grade, que é o elemento mais confiável da
    folha: ela é sempre localizada, e no modelo tem largura comparável à do
    campo Nome. CPF e RG, que dividem uma linha, ficam perto da metade disso.
    """
    grid_width = abs(grid.corners[1][0] - grid.corners[0][0])
    region_width = abs(region.corners[1][0] - region.corners[0][0])

    return region_width > grid_width * 0.7


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
