<?php

use App\Livewire\UploadCorrecao;
use Illuminate\Support\Facades\Route;

Route::get('/', UploadCorrecao::class)->name('corrigir');
Route::get('/corrigir', UploadCorrecao::class);
