<?php

namespace App\Livewire\Exams;

use App\Models\Exam;
use Illuminate\Support\Facades\DB;
use Livewire\Attributes\Layout;
use Livewire\Component;

#[Layout('components.layout')]
class ExamForm extends Component
{
    public ?Exam $exam = null;

    public string $name = '';

    public ?string $description = null;

    public ?string $applied_on = null;

    public int $questions_count = 8;

    public int $options_count = 4;

    /** @var array<int, string|null> questão => letra correta */
    public array $answerKey = [];

    public function mount(?Exam $exam = null): void
    {
        if ($exam?->exists) {
            $this->exam = $exam;
            $this->name = $exam->name;
            $this->description = $exam->description;
            $this->applied_on = $exam->applied_on?->format('Y-m-d');
            $this->questions_count = $exam->questions_count;
            $this->options_count = $exam->options_count;
            $this->answerKey = $exam->load('answerKeyItems')->answerKeyMap();

            return;
        }

        $this->syncAnswerKeySize();
    }

    /**
     * Mudar a quantidade de questões redesenha o formulário do gabarito na hora,
     * preservando o que já foi preenchido nas questões que continuam existindo.
     */
    public function updatedQuestionsCount(): void
    {
        $this->questions_count = max(1, min(60, (int) $this->questions_count));
        $this->syncAnswerKeySize();
    }

    public function updatedOptionsCount(): void
    {
        $this->options_count = max(2, min(5, (int) $this->options_count));

        // Letras que deixaram de existir são limpas, senão o gabarito guardaria
        // uma alternativa que a folha impressa não tem.
        $valid = $this->optionLetters();

        foreach ($this->answerKey as $question => $letter) {
            if ($letter !== null && ! in_array($letter, $valid, true)) {
                $this->answerKey[$question] = null;
            }
        }
    }

    public function save()
    {
        $data = $this->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string|max:255',
            'applied_on' => 'nullable|date',
            'questions_count' => 'required|integer|min:1|max:60',
            'options_count' => 'required|integer|min:2|max:5',
            'answerKey.*' => ['nullable', 'string', 'in:' . implode(',', $this->optionLetters())],
        ], attributes: [
            'name' => 'nome',
            'questions_count' => 'quantidade de questões',
            'options_count' => 'alternativas por questão',
        ]);

        $exam = DB::transaction(function () use ($data) {
            $exam = $this->exam?->exists
                ? tap($this->exam)->update($data)
                : Exam::create($data);

            // Reescreve o gabarito inteiro: simples e correto quando a
            // quantidade de questões muda. Volume aqui é dezenas de linhas.
            $exam->answerKeyItems()->delete();

            foreach ($this->answerKey as $question => $letter) {
                if ($question > $exam->questions_count || $letter === null) {
                    continue;
                }

                $exam->answerKeyItems()->create([
                    'question_number' => $question,
                    'correct_option' => $letter,
                ]);
            }

            return $exam;
        });

        session()->flash('status', 'Prova salva.');

        return $this->redirectRoute('exams.show', $exam, navigate: true);
    }

    /** @return list<string> */
    public function optionLetters(): array
    {
        return array_map(
            fn (int $i) => chr(ord('A') + $i),
            range(0, max(1, (int) $this->options_count) - 1),
        );
    }

    public function missingAnswersCount(): int
    {
        $missing = 0;

        for ($question = 1; $question <= $this->questions_count; $question++) {
            if (($this->answerKey[$question] ?? null) === null) {
                $missing++;
            }
        }

        return $missing;
    }

    private function syncAnswerKeySize(): void
    {
        $synced = [];

        for ($question = 1; $question <= $this->questions_count; $question++) {
            $synced[$question] = $this->answerKey[$question] ?? null;
        }

        $this->answerKey = $synced;
    }

    public function render()
    {
        return view('livewire.exams.exam-form');
    }
}
