<?php

use App\Livewire\Corrections\CorrectionShow;
use App\Livewire\Exams\ExamForm;
use App\Livewire\Exams\ExamIndex;
use App\Livewire\Exams\ExamShow;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/provas');

Route::get('/provas', ExamIndex::class)->name('exams.index');
Route::get('/provas/nova', ExamForm::class)->name('exams.create');
Route::get('/provas/{exam}', ExamShow::class)->name('exams.show');
Route::get('/provas/{exam}/editar', ExamForm::class)->name('exams.edit');

Route::get('/correcoes/{correction}', CorrectionShow::class)->name('corrections.show');
