<?php

namespace Database\Seeders;

use App\Models\Exam;
use Illuminate\Database\Seeder;

class ExamSeeder extends Seeder
{
    public function run(): void
    {
        $exam = Exam::firstOrCreate(
            ['name' => 'Prova de Teste'],
            ['questions_count' => 8, 'options_count' => 4],
        );

        $answerKey = ['D', 'A', 'C', 'B', 'A', 'D', 'B', 'C'];

        foreach ($answerKey as $index => $correctOption) {
            $exam->answerKeyItems()->updateOrCreate(
                ['question_number' => $index + 1],
                ['correct_option' => $correctOption],
            );
        }
    }
}
