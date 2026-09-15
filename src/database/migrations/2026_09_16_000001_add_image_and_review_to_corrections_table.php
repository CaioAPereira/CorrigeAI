<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('corrections', function (Blueprint $table) {
            // Caminho relativo no disco 'public'. Guardar a foto é o que permite
            // reconferir depois se o OMR leu a folha certo — sem ela, uma nota
            // errada não tem como ser auditada.
            $table->string('image_path')->nullable()->after('exam_id');

            // Rascunho x lançado. Uma correção nasce 'pending': o professor ainda
            // vai conferir cabeçalho e respostas. Só depois de 'reviewed' ela conta
            // como resultado válido na listagem da prova.
            $table->string('status', 20)->default('pending')->after('correct_answers_count');

            $table->timestamp('reviewed_at')->nullable()->after('status');
        });
    }

    public function down(): void
    {
        Schema::table('corrections', function (Blueprint $table) {
            $table->dropColumn(['image_path', 'status', 'reviewed_at']);
        });
    }
};
