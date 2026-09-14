<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Correction extends Model
{
    protected $fillable = ['exam_id', 'correct_answers_count'];

    protected $casts = [
        'correct_answers_count' => 'integer',
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
