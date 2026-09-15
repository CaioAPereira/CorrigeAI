<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CorrectionAnswerItem extends Model
{
    protected $fillable = [
        'correction_id',
        'question_number',
        'detected_option',
        'marked_option',
        'is_correct',
        'manually_changed',
    ];

    protected $casts = [
        'question_number' => 'integer',
        'is_correct' => 'boolean',
        'manually_changed' => 'boolean',
    ];

    public function correction(): BelongsTo
    {
        return $this->belongsTo(Correction::class);
    }
}
