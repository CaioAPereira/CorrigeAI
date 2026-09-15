<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Correction extends Model
{
    protected $fillable = [
        'exam_id',
        'correct_answers_count',
        'student_name',
        'student_cpf',
        'student_rg',
        'student_needs_review',
    ];

    protected $casts = [
        'correct_answers_count' => 'integer',
        'student_needs_review' => 'boolean',
    ];

    public function exam(): BelongsTo
    {
        return $this->belongsTo(Exam::class);
    }

    public function answerItems(): HasMany
    {
        return $this->hasMany(CorrectionAnswerItem::class);
    }
}
