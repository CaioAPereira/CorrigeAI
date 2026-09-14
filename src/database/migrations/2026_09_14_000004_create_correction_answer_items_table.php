<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('correction_answer_items', function (Blueprint $table) {
            $table->id();
            $table->foreignId('correction_id')->constrained()->cascadeOnDelete();
            $table->unsignedTinyInteger('question_number');
            $table->char('marked_option', 1)->nullable();
            $table->boolean('is_correct')->nullable();
            $table->timestamps();

            $table->unique(['correction_id', 'question_number']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('correction_answer_items');
    }
};
