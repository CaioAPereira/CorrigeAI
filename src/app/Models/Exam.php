<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Exam extends Model
{
    protected $fillable = [
        'name',
        'description',
        'applied_on',
        'questions_count',
        'options_count',
    ];

    protected $casts = [
        'applied_on' => 'date',
        'questions_count' => 'integer',
        'options_count' => 'integer',
    ];

    public function answerKeyItems(): HasMany
    {
        return $this->hasMany(AnswerKeyItem::class)->orderBy('question_number');
    }

    public function corrections(): HasMany
    {
        return $this->hasMany(Correction::class);
    }

    /**
     * Letras válidas para esta prova: A, B, C... conforme options_count.
     *
     * @return list<string>
     */
    public function optionLetters(): array
    {
        return array_map(
            fn (int $i) => chr(ord('A') + $i),
            range(0, $this->options_count - 1),
        );
    }

    /**
     * Gabarito como mapa questão => letra, pronto para preencher formulário.
     *
     * @return array<int, string|null>
     */
    public function answerKeyMap(): array
    {
        $map = $this->answerKeyItems->pluck('correct_option', 'question_number')->all();

        $filled = [];
        for ($question = 1; $question <= $this->questions_count; $question++) {
            $filled[$question] = $map[$question] ?? null;
        }

        return $filled;
    }

    /**
     * Uma prova só pode receber fotos depois que o gabarito estiver completo —
     * sem ele não há como calcular nota, e correções gravadas ficariam órfãs.
     */
    public function hasCompleteAnswerKey(): bool
    {
        return $this->answerKeyItems->count() === $this->questions_count
            && $this->answerKeyItems->every(fn (AnswerKeyItem $item) => $item->correct_option !== null);
    }
}
