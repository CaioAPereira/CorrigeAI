<?php

namespace App\Livewire\Exams;

use App\Models\Correction;
use App\Models\Exam;
use App\Services\CorrectionService;
use Livewire\Attributes\Layout;
use Livewire\Component;
use Livewire\WithFileUploads;
use RuntimeException;
use Throwable;

#[Layout('components.layout')]
class ExamShow extends Component
{
    use WithFileUploads;

    public Exam $exam;

    /** Uma foto por vez, com conferência imediata. */
    public $image;

    /** Várias fotos de uma vez; cada uma vira uma correção pendente. */
    public array $images = [];

    /** @var list<array{file: string, error: string}> */
    public array $batchErrors = [];

    public ?int $lastCorrectionId = null;

    public ?int $deletingCorrectionId = null;

    public function mount(Exam $exam): void
    {
        $this->exam = $exam->load('answerKeyItems');
    }

    /**
     * Envio individual: processa e já leva o professor para a conferência.
     */
    public function uploadSingle()
    {
        if (! $this->answerKeyIsReady('image')) {
            return null;
        }

        $this->validate([
            'image' => 'required|image|max:10240',
        ], attributes: ['image' => 'foto']);

        try {
            $correction = app(CorrectionService::class)->createFromImage($this->exam, $this->image);
        } catch (RuntimeException $e) {
            $this->addError('image', $e->getMessage());

            return null;
        }

        $this->reset('image');

        return $this->redirectRoute('corrections.show', $correction, navigate: true);
    }

    /**
     * Envio em lote: uma falha de leitura não derruba as demais fotos — o erro
     * é acumulado por arquivo e mostrado no fim, para reenviar só o que faltou.
     */
    public function uploadBatch(): void
    {
        if (! $this->answerKeyIsReady('images')) {
            return;
        }

        $this->validate([
            'images' => 'required|array|min:1',
            'images.*' => 'image|max:10240',
        ], attributes: ['images' => 'fotos', 'images.*' => 'foto']);

        $this->batchErrors = [];
        $created = 0;

        foreach ($this->images as $image) {
            try {
                app(CorrectionService::class)->createFromImage($this->exam, $image);
                $created++;
            } catch (RuntimeException|Throwable $e) {
                $this->batchErrors[] = [
                    'file' => $image->getClientOriginalName(),
                    'error' => $e->getMessage(),
                ];
            }
        }

        $this->reset('images');

        session()->flash('status', $created > 0
            ? "{$created} folha(s) processada(s). Confira cada uma antes de lançar."
            : 'Nenhuma folha pôde ser processada.');
    }

    public function confirmDeleteCorrection(int $correctionId): void
    {
        $this->deletingCorrectionId = $correctionId;
    }

    public function cancelDeleteCorrection(): void
    {
        $this->deletingCorrectionId = null;
    }

    public function deleteCorrection(): void
    {
        if ($this->deletingCorrectionId === null) {
            return;
        }

        $correction = Correction::where('exam_id', $this->exam->id)
            ->findOrFail($this->deletingCorrectionId);

        app(CorrectionService::class)->delete($correction);

        $this->deletingCorrectionId = null;

        session()->flash('status', 'Correção excluída.');
    }

    /**
     * Sem gabarito completo não há nota possível — bloqueia antes de gastar
     * tempo de OCR e de gravar correção que nasceria inválida.
     */
    private function answerKeyIsReady(string $errorBag): bool
    {
        if ($this->exam->hasCompleteAnswerKey()) {
            return true;
        }

        $this->addError($errorBag, 'Cadastre o gabarito completo desta prova antes de enviar fotos.');

        return false;
    }

    public function render()
    {
        $corrections = $this->exam->corrections()
            ->with('answerItems')
            ->latest('id')
            ->get();

        $reviewed = $corrections->where('status', Correction::STATUS_REVIEWED);

        return view('livewire.exams.exam-show', [
            'corrections' => $corrections,
            'pendingCount' => $corrections->where('status', Correction::STATUS_PENDING)->count(),
            'reviewedCount' => $reviewed->count(),
            'averageScore' => $reviewed->isNotEmpty()
                ? round($reviewed->avg('correct_answers_count'), 1)
                : null,
        ]);
    }
}
