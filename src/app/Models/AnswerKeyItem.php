<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AnswerKeyItem extends Model
{
    protected $fillable = ['exam_id', 'question_number', 'correct_option'];

    protected $casts = [
        'question_number' => 'integer',
    ];

    public function exam(): BelongsTo
    {
        return $this->belongsTo(Exam::class);
    }
}
