"""
CorrigeAI — gerador de imagens de teste do gabarito.

Cria variações sintéticas da folha no modelo atual (cabeçalho Nome/CPF/RG +
grade 8x4) para testar a leitura sem precisar imprimir e fotografar. Útil para
validar mudanças no OMR/OCR rapidamente; não substitui o teste com foto real.

Uso:
    python gerar_imagens_teste.py [pasta-de-saida]

Saída padrão: ./imagens-teste/
"""
import sys
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 660, 680

# Gabarito usado nas imagens geradas — o mesmo do ExamSeeder ("Prova de Teste").
ANSWER_KEY = ["D", "A", "C", "B", "A", "D", "B", "C"]


def build_sheet(
    answers: list[str | None],
    name: str,
    cpf: str,
    rg: str,
) -> np.ndarray:
    image = np.full((HEIGHT, WIDTH, 3), 200, np.uint8)

    cv2.rectangle(image, (18, 18), (WIDTH - 18, HEIGHT - 18), (90, 90, 90), 3)

    _draw_field(image, (120, 45), (610, 85))
    _draw_field(image, (120, 92), (325, 120))
    _draw_field(image, (400, 92), (610, 120))

    cv2.putText(image, "Nome:", (40, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(image, "CPF:", (40, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(image, "RG:", (340, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    cv2.putText(image, name, (135, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(image, cpf, (130, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(image, rg, (410, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    cv2.rectangle(image, (35, 140), (150, 635), (245, 245, 245), -1)
    cv2.rectangle(image, (35, 140), (150, 635), (60, 60, 60), 2)
    cv2.putText(image, "Questoes:", (45, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    cv2.rectangle(image, (170, 140), (600, 635), (60, 60, 60), 2)
    cv2.putText(image, "Respostas:", (330, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    _draw_grid(image, answers)

    return image


def _draw_field(image: np.ndarray, top_left, bottom_right) -> None:
    cv2.rectangle(image, top_left, bottom_right, (245, 245, 245), -1)
    cv2.rectangle(image, top_left, bottom_right, (60, 60, 60), 2)


def _draw_grid(image: np.ndarray, answers: list[str | None]) -> None:
    x1, y1, x2, y2 = 218, 228, 558, 610
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), 3)

    cell_width = (x2 - x1) / 4
    cell_height = (y2 - y1) / 8

    for column, letter in enumerate("ABCD"):
        x = int(x1 + column * cell_width + cell_width / 2) - 6
        cv2.putText(image, letter, (x, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    for row in range(8):
        cv2.putText(
            image, f"{row + 1}:", (100, int(y1 + (row + 0.6) * cell_height)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
        )

        for column in range(4):
            box_x1 = int(x1 + column * cell_width + cell_width * 0.18)
            box_y1 = int(y1 + row * cell_height + cell_height * 0.18)
            box_x2 = int(x1 + (column + 1) * cell_width - cell_width * 0.18)
            box_y2 = int(y1 + (row + 1) * cell_height - cell_height * 0.18)

            cv2.rectangle(image, (box_x1, box_y1), (box_x2, box_y2), (255, 255, 255), -1)
            cv2.rectangle(image, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 0), 2)

            if "ABCD"[column] == answers[row]:
                cv2.rectangle(
                    image, (box_x1 + 3, box_y1 + 3), (box_x2 - 3, box_y2 - 3), (10, 10, 10), -1
                )


def as_photo(image: np.ndarray) -> np.ndarray:
    """Simula foto torta: rotação leve + distorção de perspectiva."""
    source = np.float32([[0, 0], [WIDTH, 0], [WIDTH, HEIGHT], [0, HEIGHT]])
    target = np.float32([[25, 12], [WIDTH - 10, 30], [WIDTH - 30, HEIGHT - 8], [8, HEIGHT - 26]])

    return cv2.warpPerspective(
        image,
        cv2.getPerspectiveTransform(source, target),
        (WIDTH, HEIGHT),
        borderValue=(210, 210, 210),
    )


def main() -> int:
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "imagens-teste")
    output_dir.mkdir(parents=True, exist_ok=True)

    perfect = build_sheet(ANSWER_KEY, "CAIO PEREIRA", "12345678901", "445566778")

    # Folha com 2 erros e 1 questão em branco, para conferir a contagem da nota.
    partial_answers: list[str | None] = list(ANSWER_KEY)
    partial_answers[2] = "A"
    partial_answers[5] = "B"
    partial_answers[7] = None
    partial = build_sheet(partial_answers, "ANA SOUZA", "98765432100", "112233445")

    sheets = {
        "01-gabarito-perfeito.png": perfect,
        "02-gabarito-perfeito-foto.png": as_photo(perfect),
        "03-gabarito-com-erros.png": partial,
        "04-gabarito-com-erros-foto.png": as_photo(partial),
    }

    for filename, image in sheets.items():
        cv2.imwrite(str(output_dir / filename), image)
        print(f"gerado: {output_dir / filename}")

    print()
    print(f"Gabarito da 'Prova de Teste': {', '.join(ANSWER_KEY)}")
    print("Esperado — arquivos 01 e 02: 8/8 acertos, aluno CAIO PEREIRA")
    print("Esperado — arquivos 03 e 04: 5/8 acertos, aluno ANA SOUZA")

    return 0


if __name__ == "__main__":
    sys.exit(main())
