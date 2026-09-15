<?php

declare(strict_types=1);

namespace App\Services;

use App\Models\Correction;
use App\Models\Exam;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Livewire\Features\SupportFileUploads\TemporaryUploadedFile;

final class CorrectionService
{
    public function __construct(private readonly OcrClient $ocr) {}

    /**
     * Cria uma correção a partir de uma foto: guarda a imagem, lê a folha no
     * serviço OCR, grava as respostas e calcula a nota. Nasce como rascunho
     * (pending) — quem valida é o professor na tela de conferência.
     *
     * Lança RuntimeException se o serviço OCR falhar; quem chama decide se
     * aborta (envio individual) ou apenas contabiliza o erro (lote).
     */
    public function createFromImage(Exam $exam, UploadedFile $image): Correction
    {
        // Lê ANTES de persistir qualquer coisa: se o OCR falhar, não sobra
        // arquivo órfão no storage nem linha pela metade no banco.
        $sheet = $this->ocr->read($image);

        $path = $this->storeImage($exam, $image);

        $correction = DB::transaction(function () use ($exam, $sheet, $path) {
            $correction = Correction::create([
                'exam_id' => $exam->id,
                'image_path' => $path,
                'student_name' => $sheet['student']['name'],
                'student_cpf' => $sheet['student']['cpf'],
                'student_rg' => $sheet['student']['rg'],
                'student_needs_review' => $sheet['student']['needs_review'],
                'status' => Correction::STATUS_PENDING,
            ]);

            // Percorre as questões da PROVA, não as chaves devolvidas pelo OCR:
            // assim uma questão que a leitura não encontrou vira linha em branco
            // em vez de sumir da conferência.
            for ($question = 1; $question <= $exam->questions_count; $question++) {
                $detected = $sheet['answers'][$question] ?? $sheet['answers'][(string) $question] ?? null;

                $correction->answerItems()->create([
                    'question_number' => $question,
                    'detected_option' => $detected,
                    'marked_option' => $detected,
                ]);
            }

            return $correction;
        });

        $correction->load(['exam.answerKeyItems', 'answerItems']);

        $this->grade($correction);

        return $correction->refresh()->load(['exam', 'answerItems']);
    }

    /**
     * Compara respostas contra o gabarito e grava o total de acertos.
     */
    public function grade(Correction $correction): void
    {
        $answerKey = $correction->exam->answerKeyItems->keyBy('question_number');

        $correctCount = 0;

        foreach ($correction->answerItems as $answerItem) {
            $keyItem = $answerKey->get($answerItem->question_number);

            $isCorrect = $keyItem !== null
                && $answerItem->marked_option !== null
                && $answerItem->marked_option === $keyItem->correct_option;

            $answerItem->update(['is_correct' => $isCorrect]);

            if ($isCorrect) {
                $correctCount++;
            }
        }

        $correction->update(['correct_answers_count' => $correctCount]);
    }

    /**
     * Apaga a foto junto com a correção — o arquivo só existe por causa dela.
     */
    public function delete(Correction $correction): void
    {
        $path = $correction->image_path;

        $correction->delete();

        if ($path) {
            Storage::disk('public')->delete($path);
        }
    }

    private function storeImage(Exam $exam, UploadedFile $image): ?string
    {
        // Um diretório por prova mantém o storage navegável quando houver
        // várias turmas com dezenas de folhas cada.
        $directory = "gabaritos/{$exam->id}";

        if ($image instanceof TemporaryUploadedFile) {
            return $image->store($directory, 'public');
        }

        return Storage::disk('public')->putFile($directory, $image);
    }
}
