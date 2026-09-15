<?php

namespace App\Livewire\Corrections;

use App\Models\Correction;
use App\Services\CorrectionService;
use Livewire\Attributes\Layout;
use Livewire\Component;

#[Layout('components.layout')]
class CorrectionShow extends Component
{
    public Correction $correction;

    public ?string $studentName = null;

    public ?string $studentCpf = null;

    public ?string $studentRg = null;

    /** @var array<int, string|null> questão => letra marcada */
    public array $answers = [];

    public function mount(Correction $correction): void
    {
        $this->correction = $correction->load(['exam.answerKeyItems', 'answerItems']);

        $this->studentName = $correction->student_name;
        $this->studentCpf = $correction->student_cpf;
        $this->studentRg = $correction->student_rg;

        $this->answers = $correction->answerItems
            ->pluck('marked_option', 'question_number')
            ->all();
    }

    /**
     * Salva as correções manuais do professor e recalcula a nota. Marca cada
     * questão alterada para que dê para medir depois onde o OMR erra mais.
     */
    public function save(bool $andReview = false): void
    {
        $letters = $this->correction->exam->optionLetters();

        $this->validate([
            'studentName' => 'nullable|string|max:255',
            'studentCpf' => 'nullable|string|max:20',
            'studentRg' => 'nullable|string|max:20',
            'answers.*' => ['nullable', 'string', 'in:' . implode(',', $letters)],
        ], attributes: ['studentName' => 'nome']);

        $this->correction->update([
            'student_name' => $this->studentName,
            'student_cpf' => $this->studentCpf,
            'student_rg' => $this->studentRg,
            'student_needs_review' => false,
        ]);

        foreach ($this->correction->answerItems as $item) {
            $marked = $this->answers[$item->question_number] ?? null;
            $marked = $marked === '' ? null : $marked;

            $item->update([
                'marked_option' => $marked,
                'manually_changed' => $marked !== $item->detected_option,
            ]);
        }

        $this->correction->load(['exam.answerKeyItems', 'answerItems']);

        app(CorrectionService::class)->grade($this->correction);

        if ($andReview) {
            $this->correction->update([
                'status' => Correction::STATUS_REVIEWED,
                'reviewed_at' => now(),
            ]);
        }

        $this->correction = $this->correction->refresh()->load(['exam.answerKeyItems', 'answerItems']);

        session()->flash('status', $andReview
            ? 'Correção conferida e lançada.'
            : 'Alterações salvas.');
    }

    public function saveAndReview(): void
    {
        $this->save(andReview: true);
    }

    /**
     * Volta a correção para rascunho quando o professor percebe um erro depois
     * de ter lançado.
     */
    public function reopen(): void
    {
        $this->correction->update([
            'status' => Correction::STATUS_PENDING,
            'reviewed_at' => null,
        ]);

        $this->correction = $this->correction->refresh()->load(['exam.answerKeyItems', 'answerItems']);

        session()->flash('status', 'Correção reaberta para ajuste.');
    }

    public function render()
    {
        return view('livewire.corrections.correction-show', [
            'answerKey' => $this->correction->exam->answerKeyItems
                ->pluck('correct_option', 'question_number'),
            'letters' => $this->correction->exam->optionLetters(),
        ]);
    }
}
