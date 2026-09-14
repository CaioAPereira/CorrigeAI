<?php

use App\Livewire\UploadCorrecao;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

Route::get('/corrigir', UploadCorrecao::class)->name('corrigir');
