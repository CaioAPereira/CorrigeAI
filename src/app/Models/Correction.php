<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Correction extends Model
{
    public const STATUS_PENDING = 'pending';

    public const STATUS_REVIEWED = 'reviewed';

    protected $fillable = [
        'exam_id',
        'image_path',
        'student_name',
        'student_cpf',
        'student_rg',
        'student_needs_review',
        'correct_answers_count',
        'status',
        'reviewed_at',
    ];

    protected $casts = [
        'correct_answers_count' => 'integer',
        'student_needs_review' => 'boolean',
        'reviewed_at' => 'datetime',
    ];

    public function exam(): BelongsTo
    {
        return $this->belongsTo(Exam::class);
    }

    public function answerItems(): HasMany
    {
        return $this->hasMany(CorrectionAnswerItem::class)->orderBy('question_number');
    }

    public function isReviewed(): bool
    {
        return $this->status === self::STATUS_REVIEWED;
    }

    /**
     * Percentual de acerto sobre o total de questões da prova (e não sobre as
     * questões lidas): uma folha em que o OMR só achou 6 de 8 questões não pode
     * parecer melhor do que é.
     */
    public function scorePercent(): float
    {
        $total = $this->exam?->questions_count ?? 0;

        if ($total === 0) {
            return 0.0;
        }

        return round((($this->correct_answers_count ?? 0) / $total) * 100, 1);
    }

    public function studentLabel(): string
    {
        return filled($this->student_name)
            ? $this->student_name
            : 'Aluno não identificado';
    }
}
