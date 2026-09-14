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

#[Layout('components.layout')]
class UploadCorrecao extends Component
{
    use WithFileUploads;

    public ?int $examId = null;

    public $image;

    public ?int $correctAnswersCount = null;

    public function save(): void
    {
        $this->validate([
            'examId' => 'required|exists:exams,id',
            'image' => 'required|image|max:10240',
        ]);

        $exam = Exam::findOrFail($this->examId);

        $answers = app(OcrClient::class)->read($this->image);

        $correction = DB::transaction(function () use ($exam, $answers) {
            $correction = Correction::create(['exam_id' => $exam->id]);

            foreach ($answers as $questionNumber => $markedOption) {
                $correction->answerItems()->create([
                    'question_number' => $questionNumber,
                    'marked_option' => $markedOption,
                ]);
            }

            return $correction;
        });

        $correction->load(['exam.answerKeyItems', 'answerItems']);

        app(CorrectionService::class)->grade($correction);

        $this->correctAnswersCount = $correction->refresh()->correct_answers_count;
    }

    public function render()
    {
        return view('livewire.upload-correcao', [
            'exams' => Exam::all(),
        ]);
    }
}
