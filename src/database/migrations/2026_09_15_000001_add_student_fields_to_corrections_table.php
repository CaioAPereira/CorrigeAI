<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('corrections', function (Blueprint $table) {
            // Texto bruto lido do cabeçalho pelo OCR. Nullable: a foto pode
            // cortar o cabeçalho, ou o campo pode vir ilegível/em branco.
            $table->string('student_name')->nullable()->after('exam_id');
            $table->string('student_cpf', 20)->nullable()->after('student_name');
            $table->string('student_rg', 20)->nullable()->after('student_cpf');

            // Sinaliza leitura de baixa confiança para o professor conferir
            // antes de considerar a identificação correta.
            $table->boolean('student_needs_review')->default(false)->after('student_rg');
        });
    }

    public function down(): void
    {
        Schema::table('corrections', function (Blueprint $table) {
            $table->dropColumn([
                'student_name',
                'student_cpf',
                'student_rg',
                'student_needs_review',
            ]);
        });
    }
};
