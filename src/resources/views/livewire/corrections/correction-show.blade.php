<div class="space-y-6">
    <div class="flex items-center gap-2 text-sm text-slate-500">
        <a href="{{ route('exams.index') }}" wire:navigate class="hover:text-slate-900">Provas</a>
        <span>/</span>
        <a href="{{ route('exams.show', $correction->exam) }}" wire:navigate class="hover:text-slate-900">
            {{ $correction->exam->name }}
        </a>
        <span>/</span>
        <span class="text-slate-900">Conferência</span>
    </div>

    <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
            <h1 class="text-2xl font-semibold tracking-tight">{{ $correction->studentLabel() }}</h1>
            <p class="mt-1 text-sm text-slate-500">
                Lançada em {{ $correction->created_at->format('d/m/Y H:i') }}
                @if ($correction->isReviewed() && $correction->reviewed_at)
                    · conferida em {{ $correction->reviewed_at->format('d/m/Y H:i') }}
                @endif
            </p>
        </div>

        @if ($correction->isReviewed())
            <span class="rounded-full bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-800">Conferida</span>
        @else
            <span class="rounded-full bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800">Aguardando conferência</span>
        @endif
    </div>

    <div class="grid gap-6 lg:grid-cols-5">
        <section class="lg:col-span-2 space-y-6">
            <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 class="text-base font-semibold">Nota</h2>

                <div class="mt-4 flex items-baseline gap-2">
                    <span class="text-4xl font-semibold tracking-tight text-indigo-600">
                        {{ $correction->correct_answers_count ?? 0 }}
                    </span>
                    <span class="text-lg text-slate-400">/ {{ $correction->exam->questions_count }}</span>
                    <span class="ml-auto text-sm font-medium text-slate-500">{{ $correction->scorePercent() }}%</span>
                </div>

                <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div class="h-full rounded-full bg-indigo-600 transition-all"
                         style="width: {{ $correction->scorePercent() }}%"></div>
                </div>
            </div>

            <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div class="border-b border-slate-200 px-6 py-4">
                    <h2 class="text-base font-semibold">Foto enviada</h2>
                    <p class="mt-1 text-sm text-slate-500">Compare com o que a leitura identificou.</p>
                </div>

                @if ($correction->image_path)
                    <a href="{{ Storage::disk('public')->url($correction->image_path) }}" target="_blank" rel="noopener">
                        <img src="{{ Storage::disk('public')->url($correction->image_path) }}"
                             alt="Folha de gabarito enviada"
                             class="w-full bg-slate-100 object-contain">
                    </a>
                @else
                    <p class="px-6 py-10 text-center text-sm text-slate-500">Foto não disponível.</p>
                @endif
            </div>
        </section>

        <section class="lg:col-span-3 space-y-6">
            <form wire:submit="save" class="space-y-6">
                <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div class="flex items-start justify-between gap-4">
                        <div>
                            <h2 class="text-base font-semibold">Identificação do aluno</h2>
                            <p class="mt-1 text-sm text-slate-500">Ajuste o que o OCR não acertou.</p>
                        </div>

                        @if ($correction->student_needs_review)
                            <span class="shrink-0 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                                Revisar leitura
                            </span>
                        @endif
                    </div>

                    <div class="mt-5 space-y-4">
                        <div>
                            <label for="studentName" class="block text-sm font-medium text-slate-700">Nome</label>
                            <input type="text" id="studentName" wire:model="studentName"
                                   class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                            @error('studentName') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                        </div>

                        <div class="grid gap-4 sm:grid-cols-2">
                            <div>
                                <label for="studentCpf" class="block text-sm font-medium text-slate-700">CPF</label>
                                <input type="text" id="studentCpf" wire:model="studentCpf"
                                       class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                                @error('studentCpf') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                            </div>

                            <div>
                                <label for="studentRg" class="block text-sm font-medium text-slate-700">RG</label>
                                <input type="text" id="studentRg" wire:model="studentRg"
                                       class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                                @error('studentRg') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                            </div>
                        </div>
                    </div>
                </div>

                <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div class="border-b border-slate-200 px-6 py-4">
                        <h2 class="text-base font-semibold">Respostas</h2>
                        <p class="mt-1 text-sm text-slate-500">
                            Clique para trocar a alternativa quando a leitura estiver errada.
                            O botão cinza "—" marca a questão como em branco.
                        </p>
                    </div>

                    <div class="divide-y divide-slate-100">
                        @foreach ($correction->answerItems as $item)
                            @php
                                $expected = $answerKey[$item->question_number] ?? null;
                                $current = $answers[$item->question_number] ?? null;
                                $hit = $current !== null && $current === $expected;
                            @endphp

                            <div class="flex flex-wrap items-center gap-4 px-6 py-3">
                                <span class="w-6 shrink-0 text-sm font-medium text-slate-500">{{ $item->question_number }}</span>

                                <div class="flex flex-wrap gap-1.5">
                                    @foreach ($letters as $letter)
                                        <label class="cursor-pointer">
                                            <input type="radio" class="peer sr-only"
                                                   wire:model.live="answers.{{ $item->question_number }}" value="{{ $letter }}">
                                            <span class="flex size-8 items-center justify-center rounded-md border border-slate-300 text-sm font-medium text-slate-600 transition hover:bg-slate-50 peer-checked:border-indigo-600 peer-checked:bg-indigo-600 peer-checked:text-white">
                                                {{ $letter }}
                                            </span>
                                        </label>
                                    @endforeach

                                    <label class="cursor-pointer">
                                        <input type="radio" class="peer sr-only"
                                               wire:model.live="answers.{{ $item->question_number }}" value="">
                                        <span class="flex size-8 items-center justify-center rounded-md border border-slate-300 text-sm font-medium text-slate-400 transition hover:bg-slate-50 peer-checked:border-slate-600 peer-checked:bg-slate-600 peer-checked:text-white">
                                            —
                                        </span>
                                    </label>
                                </div>

                                <div class="ml-auto flex items-center gap-3 text-xs">
                                    <span class="text-slate-500">gabarito: <strong class="text-slate-700">{{ $expected ?? '—' }}</strong></span>

                                    @if ($item->manually_changed)
                                        <span class="rounded-full bg-sky-100 px-2 py-0.5 font-medium text-sky-800"
                                              title="Leitura original: {{ $item->detected_option ?? 'em branco' }}">
                                            ajustada
                                        </span>
                                    @endif

                                    @if ($hit)
                                        <span class="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800">certa</span>
                                    @else
                                        <span class="rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-800">errada</span>
                                    @endif
                                </div>
                            </div>
                        @endforeach
                    </div>
                </div>

                <div class="flex flex-wrap items-center gap-3">
                    @if ($correction->isReviewed())
                        <button type="submit"
                                class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700">
                            Salvar alterações
                        </button>
                        <button type="button" wire:click="reopen"
                                class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50">
                            Reabrir para ajuste
                        </button>
                    @else
                        <button type="button" wire:click="saveAndReview"
                                class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700">
                            Confirmar e lançar
                        </button>
                        <button type="submit"
                                class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50">
                            Salvar sem lançar
                        </button>
                    @endif

                    <a href="{{ route('exams.show', $correction->exam) }}" wire:navigate
                       class="text-sm font-medium text-slate-600 hover:text-slate-900">Voltar para a prova</a>

                    <span wire:loading wire:target="save,saveAndReview" class="text-sm text-slate-500">Salvando...</span>
                </div>
            </form>
        </section>
    </div>
</div>
