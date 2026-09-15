<?php

declare(strict_types=1);

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use RuntimeException;

final class OcrClient
{
    /**
     * Lê a folha inteira: dados do aluno no cabeçalho + respostas marcadas.
     *
     * @return array{
     *     student: array{name: ?string, cpf: ?string, rg: ?string, needs_review: bool},
     *     answers: array<int|string, string|null>
     * }
     */
    public function read(UploadedFile $image): array
    {
        try {
            $response = Http::timeout(120)->attach(
                'file',
                fopen($image->getRealPath(), 'r'),
                $image->getClientOriginalName(),
            )->post(config('services.ocr.url') . '/read');
        } catch (ConnectionException $e) {
            throw new RuntimeException('Serviço OCR indisponível.', previous: $e);
        }

        if (! $response->successful()) {
            throw new RuntimeException('Falha ao processar imagem no serviço OCR.');
        }

        $payload = $response->json();

        return [
            'student' => $this->normalizeStudent($payload['student'] ?? []),
            'answers' => $payload['answers'] ?? [],
        ];
    }

    /**
     * Achata a resposta do serviço (que traz confiança e motor por campo) no
     * formato que a aplicação grava: o texto de cada campo, mais um único
     * sinalizador de revisão se qualquer um deles veio com baixa confiança.
     *
     * @param  array<string, mixed>  $student
     * @return array{name: ?string, cpf: ?string, rg: ?string, needs_review: bool}
     */
    private function normalizeStudent(array $student): array
    {
        $needsReview = false;

        foreach (['name', 'cpf', 'rg'] as $field) {
            if (($student[$field]['needs_review'] ?? true) === true) {
                $needsReview = true;
            }
        }

        return [
            'name' => $student['name']['text'] ?? null,
            'cpf' => $student['cpf']['text'] ?? null,
            'rg' => $student['rg']['text'] ?? null,
            'needs_review' => $needsReview,
        ];
    }
}
