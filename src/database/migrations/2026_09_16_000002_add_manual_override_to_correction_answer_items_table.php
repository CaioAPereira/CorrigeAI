<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('correction_answer_items', function (Blueprint $table) {
            // O que o OMR leu originalmente. Preservar isso separado de
            // marked_option permite mostrar "o sistema leu B, o professor
            // corrigiu para C" e medir a acurácia real da leitura.
            $table->char('detected_option', 1)->nullable()->after('question_number');

            $table->boolean('manually_changed')->default(false)->after('is_correct');
        });
    }

    public function down(): void
    {
        Schema::table('correction_answer_items', function (Blueprint $table) {
            $table->dropColumn(['detected_option', 'manually_changed']);
        });
    }
};
