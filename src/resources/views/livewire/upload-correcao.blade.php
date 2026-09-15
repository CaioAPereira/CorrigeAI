<div class="space-y-8">
    <div>
        <h1 class="text-2xl font-semibold tracking-tight">Corrigir gabarito</h1>
        <p class="mt-1 text-sm text-slate-500">
            Envie a foto da folha preenchida. O sistema identifica o aluno pelo cabeçalho e confere as respostas.
        </p>
    </div>

    <form wire:submit="save" class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div class="grid gap-6 sm:grid-cols-2">
            <div>
                <label for="examId" class="block text-sm font-medium text-slate-700">Prova</label>
                <select id="examId" wire:model="examId"
                        class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    <option value="">Selecione a prova</option>
                    @foreach ($exams as $exam)
                        <option value="{{ $exam->id }}">{{ $exam->name }}</option>
                    @endforeach
                </select>
                @error('examId')
                    <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p>
                @enderror
            </div>

            <div>
                <label for="image" class="block text-sm font-medium text-slate-700">Foto do gabarito</label>
                <input type="file" id="image" wire:model="image" accept="image/*"
                       class="mt-2 w-full cursor-pointer rounded-lg border border-slate-300 bg-white text-sm text-slate-600 shadow-sm file:mr-3 file:cursor-pointer file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                @error('image')
                    <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p>
                @enderror
            </div>
        </div>

        <div class="mt-6 flex items-center gap-3">
            <button type="submit" wire:loading.attr="disabled" wire:target="save,image"
                    class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-300 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60">
                Corrigir
            </button>

            <span wire:loading wire:target="save" class="flex items-center gap-2 text-sm text-slate-500">
                <svg class="size-4 animate-spin text-indigo-600" viewBox="0 0 24 24" fill="none">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                </svg>
                Lendo a folha...
            </span>

            <span wire:loading wire:target="image" class="text-sm text-slate-500">Carregando imagem...</span>
        </div>

        @error('ocr')
            <p class="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{{ $message }}</p>
        @enderror
    </form>

    @if ($correction)
        @php
            $total = $correction->answerItems->count();
            $acertos = $correction->correct_answers_count ?? 0;
        @endphp

        <div class="grid gap-6 lg:grid-cols-5">
            <section class="lg:col-span-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div class="flex items-start justify-between gap-4">
                    <div>
                        <h2 class="text-base font-semibold">Aluno identificado</h2>
                        <p class="mt-1 text-sm text-slate-500">Confira e ajuste o que a leitura não acertou.</p>
                    </div>

                    @if ($correction->student_needs_review)
                        <span class="shrink-0 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                            Revisar leitura
                        </span>
                    @else
                        <span class="shrink-0 rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
                            Leitura confiável
                        </span>
                    @endif
                </div>

                <form wire:submit="confirmStudent" class="mt-5 space-y-4">
                    <div>
                        <label for="studentName" class="block text-sm font-medium text-slate-700">Nome</label>
                        <input type="text" id="studentName" wire:model="studentName"
                               class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    </div>

                    <div class="grid gap-4 sm:grid-cols-2">
                        <div>
                            <label for="studentCpf" class="block text-sm font-medium text-slate-700">CPF</label>
                            <input type="text" id="studentCpf" wire:model="studentCpf"
                                   class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                        </div>

                        <div>
                            <label for="studentRg" class="block text-sm font-medium text-slate-700">RG</label>
                            <input type="text" id="studentRg" wire:model="studentRg"
                                   class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                        </div>
                    </div>

                    <div class="flex items-center gap-3 pt-1">
                        <button type="submit"
                                class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                            Confirmar dados
                        </button>

                        <span wire:loading wire:target="confirmStudent" class="text-sm text-slate-500">Salvando...</span>

                        @if (session('student-confirmed'))
                            <span class="text-sm text-emerald-600">Dados confirmados.</span>
                        @endif
                    </div>
                </form>
            </section>

            <section class="lg:col-span-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 class="text-base font-semibold">Resultado</h2>

                <div class="mt-4 flex items-baseline gap-2">
                    <span class="text-4xl font-semibold tracking-tight text-indigo-600">{{ $acertos }}</span>
                    <span class="text-lg text-slate-400">/ {{ $total }}</span>
                </div>

                <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div class="h-full rounded-full bg-indigo-600 transition-all"
                         style="width: {{ $total > 0 ? ($acertos / $total) * 100 : 0 }}%"></div>
                </div>

                <p class="mt-3 text-sm text-slate-500">
                    {{ $correction->exam->name }}
                </p>
            </section>
        </div>

        <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div class="border-b border-slate-200 px-6 py-4">
                <h2 class="text-base font-semibold">Respostas</h2>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-slate-50 text-left text-xs font-medium tracking-wide text-slate-500 uppercase">
                        <tr>
                            <th class="px-6 py-3">Questão</th>
                            <th class="px-6 py-3">Marcada</th>
                            <th class="px-6 py-3">Resultado</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        @foreach ($correction->answerItems->sortBy('question_number') as $item)
                            <tr class="hover:bg-slate-50">
                                <td class="px-6 py-3 font-medium">{{ $item->question_number }}</td>
                                <td class="px-6 py-3">
                                    @if ($item->marked_option)
                                        <span class="inline-flex size-7 items-center justify-center rounded-md bg-slate-100 font-medium">
                                            {{ $item->marked_option }}
                                        </span>
                                    @else
                                        <span class="text-slate-400">em branco</span>
                                    @endif
                                </td>
                                <td class="px-6 py-3">
                                    @if ($item->is_correct)
                                        <span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">Correta</span>
                                    @else
                                        <span class="rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-800">Errada</span>
                                    @endif
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </section>
    @endif
</div>
