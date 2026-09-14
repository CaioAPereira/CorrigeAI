<?php

declare(strict_types=1);

namespace App\Services;

use App\Models\Correction;

final class CorrectionService
{
    public function grade(Correction $correction): void
    {
        $answerKey = $correction->exam->answerKeyItems
            ->keyBy('question_number');

        $answerItems = $correction->answerItems;

        $correctCount = 0;

        foreach ($answerItems as $answerItem) {
            $keyItem = $answerKey->get($answerItem->question_number);

            $isCorrect = $keyItem !== null
                && $answerItem->marked_option === $keyItem->correct_option;

            $answerItem->update(['is_correct' => $isCorrect]);

            if ($isCorrect) {
                $correctCount++;
            }
        }

        $correction->update(['correct_answers_count' => $correctCount]);
    }
}
