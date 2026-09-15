<?php

namespace App\Livewire;

use App\Models\Correction;
use App\Models\Exam;
use App\Services\CorrectionService;
use App\Services\OcrClient;
use Illuminate\Support\Facades\DB;
use Livewire\Attributes\Layout;
use Livewire\Component;
use Livewire\WithFileUploads;
use RuntimeException;

#[Layout('components.layout')]
class UploadCorrecao extends Component
{
    use WithFileUploads;

    public ?int $examId = null;

    public $image;

    public ?Correction $correction = null;

    // Campos do cabeçalho ficam como propriedades simples, e não amarrados ao
    // Model via wire:model: o binding em atributo de Eloquent exige declaração
    // extra no Livewire e o campo chega vazio na tela sem ela.
    public ?string $studentName = null;

    public ?string $studentCpf = null;

    public ?string $studentRg = null;

    public function save(): void
    {
        $this->validate([
            'examId' => 'required|exists:exams,id',
            'image' => 'required|image|max:10240',
        ]);

        $exam = Exam::findOrFail($this->examId);

        try {
            $sheet = app(OcrClient::class)->read($this->image);
        } catch (RuntimeException $e) {
            $this->addError('ocr', $e->getMessage());

            return;
        }

        $correction = DB::transaction(function () use ($exam, $sheet) {
            $correction = Correction::create([
                'exam_id' => $exam->id,
                'student_name' => $sheet['student']['name'],
                'student_cpf' => $sheet['student']['cpf'],
                'student_rg' => $sheet['student']['rg'],
                'student_needs_review' => $sheet['student']['needs_review'],
            ]);

            foreach ($sheet['answers'] as $questionNumber => $markedOption) {
                $correction->answerItems()->create([
                    'question_number' => $questionNumber,
                    'marked_option' => $markedOption,
                ]);
            }

            return $correction;
        });

        $correction->load(['exam.answerKeyItems', 'answerItems']);

        app(CorrectionService::class)->grade($correction);

        $this->correction = $correction->refresh()->load('answerItems');

        $this->studentName = $this->correction->student_name;
        $this->studentCpf = $this->correction->student_cpf;
        $this->studentRg = $this->correction->student_rg;
    }

    /**
     * Permite ao professor corrigir à mão o que o OCR leu errado no cabeçalho.
     */
    public function confirmStudent(): void
    {
        $this->validate([
            'studentName' => 'nullable|string|max:255',
            'studentCpf' => 'nullable|string|max:20',
            'studentRg' => 'nullable|string|max:20',
        ]);

        $this->correction->update([
            'student_name' => $this->studentName,
            'student_cpf' => $this->studentCpf,
            'student_rg' => $this->studentRg,
            'student_needs_review' => false,
        ]);

        session()->flash('student-confirmed', true);
    }

    public function render()
    {
        return view('livewire.upload-correcao', [
            'exams' => Exam::all(),
        ]);
    }
}
