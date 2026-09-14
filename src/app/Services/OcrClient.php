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
     * @return array<int, string|null> mapa question_number => marked_option
     */
    public function read(UploadedFile $image): array
    {
        try {
            $response = Http::attach(
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

        return $response->json();
    }
}
