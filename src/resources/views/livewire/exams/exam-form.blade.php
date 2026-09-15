<div class="space-y-6">
    <div class="flex items-center gap-2 text-sm text-slate-500">
        <a href="{{ route('exams.index') }}" wire:navigate class="hover:text-slate-900">Provas</a>
        <span>/</span>
        <span class="text-slate-900">{{ $exam?->exists ? 'Editar' : 'Nova prova' }}</span>
    </div>

    <div>
        <h1 class="text-2xl font-semibold tracking-tight">
            {{ $exam?->exists ? 'Editar prova' : 'Nova prova' }}
        </h1>
        <p class="mt-1 text-sm text-slate-500">
            O gabarito precisa estar completo antes de lançar fotos das folhas.
        </p>
    </div>

    <form wire:submit="save" class="space-y-6">
        <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 class="text-base font-semibold">Dados da prova</h2>

            <div class="mt-5 grid gap-5 sm:grid-cols-2">
                <div class="sm:col-span-2">
                    <label for="name" class="block text-sm font-medium text-slate-700">Nome</label>
                    <input type="text" id="name" wire:model="name" placeholder="Ex.: Matemática — 3º bimestre"
                           class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    @error('name') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                </div>

                <div class="sm:col-span-2">
                    <label for="description" class="block text-sm font-medium text-slate-700">
                        Descrição <span class="font-normal text-slate-400">(opcional)</span>
                    </label>
                    <input type="text" id="description" wire:model="description" placeholder="Turma, disciplina, observações"
                           class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    @error('description') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                </div>

                <div>
                    <label for="applied_on" class="block text-sm font-medium text-slate-700">Data de aplicação</label>
                    <input type="date" id="applied_on" wire:model="applied_on"
                           class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    @error('applied_on') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label for="questions_count" class="block text-sm font-medium text-slate-700">Questões</label>
                        <input type="number" id="questions_count" min="1" max="60" wire:model.live="questions_count"
                               class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                        @error('questions_count') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                    </div>

                    <div>
                        <label for="options_count" class="block text-sm font-medium text-slate-700">Alternativas</label>
                        <input type="number" id="options_count" min="2" max="5" wire:model.live="options_count"
                               class="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                        @error('options_count') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                    </div>
                </div>
            </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div class="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 class="text-base font-semibold">Gabarito</h2>
                    <p class="mt-1 text-sm text-slate-500">Marque a alternativa correta de cada questão.</p>
                </div>

                @if ($this->missingAnswersCount() > 0)
                    <span class="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                        Faltam {{ $this->missingAnswersCount() }} questão(ões)
                    </span>
                @else
                    <span class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
                        Gabarito completo
                    </span>
                @endif
            </div>

            <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                @for ($question = 1; $question <= $questions_count; $question++)
                    <div class="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2">
                        <span class="w-8 shrink-0 text-sm font-medium text-slate-500">{{ $question }}</span>

                        <div class="flex flex-wrap gap-1.5">
                            @foreach ($this->optionLetters() as $letter)
                                <label class="cursor-pointer">
                                    <input type="radio" class="peer sr-only"
                                           wire:model.live="answerKey.{{ $question }}" value="{{ $letter }}">
                                    <span class="flex size-8 items-center justify-center rounded-md border border-slate-300 text-sm font-medium text-slate-600 transition hover:bg-slate-50 peer-checked:border-indigo-600 peer-checked:bg-indigo-600 peer-checked:text-white">
                                        {{ $letter }}
                                    </span>
                                </label>
                            @endforeach
                        </div>
                    </div>
                @endfor
            </div>

            @error('answerKey.*') <p class="mt-3 text-xs text-red-600">{{ $message }}</p> @enderror
        </section>

        <div class="flex items-center gap-3">
            <button type="submit" wire:loading.attr="disabled"
                    class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
                Salvar prova
            </button>

            <a href="{{ $exam?->exists ? route('exams.show', $exam) : route('exams.index') }}" wire:navigate
               class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50">
                Cancelar
            </a>

            <span wire:loading wire:target="save" class="text-sm text-slate-500">Salvando...</span>
        </div>
    </form>
</div>
