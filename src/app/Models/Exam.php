<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Exam extends Model
{
    protected $fillable = [
        'name',
        'questions_count',
        'options_count',
    ];

    protected $casts = [
        'questions_count' => 'integer',
        'options_count' => 'integer',
    ];

    public function answerKeyItems(): HasMany
    {
        return $this->hasMany(AnswerKeyItem::class);
    }

    public function corrections(): HasMany
    {
        return $this->hasMany(Correction::class);
    }
}
