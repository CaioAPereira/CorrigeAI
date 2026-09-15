<div class="space-y-6" x-data="{ mode: 'single' }">
    <div class="flex items-center gap-2 text-sm text-slate-500">
        <a href="{{ route('exams.index') }}" wire:navigate class="hover:text-slate-900">Provas</a>
        <span>/</span>
        <span class="text-slate-900">{{ $exam->name }}</span>
    </div>

    <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
            <h1 class="text-2xl font-semibold tracking-tight">{{ $exam->name }}</h1>
            <p class="mt-1 text-sm text-slate-500">
                {{ $exam->questions_count }} questões · {{ $exam->options_count }} alternativas
                @if ($exam->applied_on) · aplicada em {{ $exam->applied_on->format('d/m/Y') }} @endif
            </p>
        </div>

        <a href="{{ route('exams.edit', $exam) }}" wire:navigate
           class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50">
            Editar prova e gabarito
        </a>
    </div>

    <div class="grid gap-4 sm:grid-cols-4">
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-medium tracking-wide text-slate-500 uppercase">Folhas lançadas</p>
            <p class="mt-2 text-3xl font-semibold tracking-tight">{{ $corrections->count() }}</p>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-medium tracking-wide text-slate-500 uppercase">Aguardando conferência</p>
            <p class="mt-2 text-3xl font-semibold tracking-tight text-amber-600">{{ $pendingCount }}</p>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-medium tracking-wide text-slate-500 uppercase">Conferidas</p>
            <p class="mt-2 text-3xl font-semibold tracking-tight text-emerald-600">{{ $reviewedCount }}</p>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-medium tracking-wide text-slate-500 uppercase">Média (conferidas)</p>
            <p class="mt-2 text-3xl font-semibold tracking-tight">
                {{ $averageScore !== null ? $averageScore : '—' }}
                @if ($averageScore !== null)
                    <span class="text-lg font-normal text-slate-400">/ {{ $exam->questions_count }}</span>
                @endif
            </p>
        </div>
    </div>

    @unless ($exam->hasCompleteAnswerKey())
        <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-4">
            <p class="text-sm font-medium text-amber-900">Gabarito incompleto</p>
            <p class="mt-1 text-sm text-amber-800">
                Esta prova tem {{ $exam->answerKeyItems->count() }} de {{ $exam->questions_count }} questões no gabarito.
                Complete-o antes de enviar fotos — sem ele não há como calcular nota.
            </p>
            <a href="{{ route('exams.edit', $exam) }}" wire:navigate
               class="mt-3 inline-block rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700">
                Completar gabarito
            </a>
        </div>
    @endunless

    <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4">
            <div>
                <h2 class="text-base font-semibold">Lançar folhas</h2>
                <p class="mt-1 text-sm text-slate-500">Cada foto vira uma correção para você conferir.</p>
            </div>

            <div class="flex rounded-lg border border-slate-300 bg-slate-50 p-1 text-sm">
                <button type="button" @click="mode = 'single'"
                        :class="mode === 'single' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-600'"
                        class="rounded-md px-3 py-1.5 font-medium transition">Uma por vez</button>
                <button type="button" @click="mode = 'batch'"
                        :class="mode === 'batch' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-600'"
                        class="rounded-md px-3 py-1.5 font-medium transition">Em lote</button>
            </div>
        </div>

        <div class="px-6 py-5">
            <div x-show="mode === 'single'">
                <form wire:submit="uploadSingle">
                    <label for="image" class="block text-sm font-medium text-slate-700">Foto da folha</label>
                    <input type="file" id="image" wire:model="image" accept="image/*"
                           class="mt-2 w-full cursor-pointer rounded-lg border border-slate-300 bg-white text-sm text-slate-600 shadow-sm file:mr-3 file:cursor-pointer file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    @error('image') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror

                    <p class="mt-2 text-xs text-slate-500">
                        Ao processar, você vai direto para a tela de conferência desta folha.
                    </p>

                    <div class="mt-4 flex items-center gap-3">
                        <button type="submit" wire:loading.attr="disabled" wire:target="uploadSingle,image"
                                class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
                            Processar folha
                        </button>

                        <span wire:loading wire:target="uploadSingle" class="flex items-center gap-2 text-sm text-slate-500">
                            <svg class="size-4 animate-spin text-indigo-600" viewBox="0 0 24 24" fill="none">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                            </svg>
                            Lendo a folha...
                        </span>
                        <span wire:loading wire:target="image" class="text-sm text-slate-500">Carregando imagem...</span>
                    </div>
                </form>
            </div>

            <div x-show="mode === 'batch'" x-cloak>
                <form wire:submit="uploadBatch">
                    <label for="images" class="block text-sm font-medium text-slate-700">Fotos das folhas</label>
                    <input type="file" id="images" wire:model="images" accept="image/*" multiple
                           class="mt-2 w-full cursor-pointer rounded-lg border border-slate-300 bg-white text-sm text-slate-600 shadow-sm file:mr-3 file:cursor-pointer file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
                    @error('images') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror
                    @error('images.*') <p class="mt-1.5 text-xs text-red-600">{{ $message }}</p> @enderror

                    @if (count($images) > 0)
                        <p class="mt-2 text-sm text-slate-600">{{ count($images) }} arquivo(s) selecionado(s).</p>
                    @endif

                    <p class="mt-2 text-xs text-slate-500">
                        Todas as folhas ficam como <strong>aguardando conferência</strong> na lista abaixo.
                        Uma foto ilegível não interrompe as demais.
                    </p>

                    <div class="mt-4 flex items-center gap-3">
                        <button type="submit" wire:loading.attr="disabled" wire:target="uploadBatch,images"
                                class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
                            Processar lote
                        </button>

                        <span wire:loading wire:target="uploadBatch" class="flex items-center gap-2 text-sm text-slate-500">
                            <svg class="size-4 animate-spin text-indigo-600" viewBox="0 0 24 24" fill="none">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                            </svg>
                            Processando folhas, isso pode demorar...
                        </span>
                        <span wire:loading wire:target="images" class="text-sm text-slate-500">Carregando imagens...</span>
                    </div>
                </form>

                @if (count($batchErrors) > 0)
                    <div class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                        <p class="text-sm font-medium text-red-900">Estas folhas não puderam ser lidas:</p>
                        <ul class="mt-2 space-y-1 text-sm text-red-800">
                            @foreach ($batchErrors as $failure)
                                <li>• <strong>{{ $failure['file'] }}</strong> — {{ $failure['error'] }}</li>
                            @endforeach
                        </ul>
                    </div>
                @endif
            </div>
        </div>
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-200 px-6 py-4">
            <h2 class="text-base font-semibold">Correções desta prova</h2>
        </div>

        @if ($corrections->isEmpty())
            <p class="px-6 py-12 text-center text-sm text-slate-500">
                Nenhuma folha lançada ainda.
            </p>
        @else
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-slate-50 text-left text-xs font-medium tracking-wide text-slate-500 uppercase">
                        <tr>
                            <th class="px-6 py-3">Aluno</th>
                            <th class="px-6 py-3">CPF</th>
                            <th class="px-6 py-3">Nota</th>
                            <th class="px-6 py-3">Situação</th>
                            <th class="px-6 py-3">Lançada em</th>
                            <th class="px-6 py-3 text-right">Ações</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        @foreach ($corrections as $correction)
                            <tr class="hover:bg-slate-50">
                                <td class="px-6 py-4">
                                    <a href="{{ route('corrections.show', $correction) }}" wire:navigate
                                       class="font-medium text-indigo-600 hover:text-indigo-800">
                                        {{ $correction->studentLabel() }}
                                    </a>
                                    @if ($correction->student_needs_review)
                                        <span class="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                                            leitura incerta
                                        </span>
                                    @endif
                                </td>
                                <td class="px-6 py-4 text-slate-600">{{ $correction->student_cpf ?? '—' }}</td>
                                <td class="px-6 py-4">
                                    <span class="font-medium">{{ $correction->correct_answers_count ?? 0 }}</span>
                                    <span class="text-slate-400">/ {{ $exam->questions_count }}</span>
                                    <span class="ml-2 text-xs text-slate-500">({{ $correction->scorePercent() }}%)</span>
                                </td>
                                <td class="px-6 py-4">
                                    @if ($correction->isReviewed())
                                        <span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
                                            Conferida
                                        </span>
                                    @else
                                        <span class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                                            Aguardando
                                        </span>
                                    @endif
                                </td>
                                <td class="px-6 py-4 text-slate-600">{{ $correction->created_at->format('d/m/Y H:i') }}</td>
                                <td class="px-6 py-4">
                                    <div class="flex items-center justify-end gap-3">
                                        <a href="{{ route('corrections.show', $correction) }}" wire:navigate
                                           class="text-sm font-medium text-slate-600 hover:text-slate-900">Conferir</a>
                                        <button type="button" wire:click="confirmDeleteCorrection({{ $correction->id }})"
                                                class="text-sm font-medium text-red-600 hover:text-red-800">Excluir</button>
                                    </div>
                                </td>
                            </tr>

                            @if ($deletingCorrectionId === $correction->id)
                                <tr class="bg-red-50">
                                    <td colspan="6" class="px-6 py-4">
                                        <div class="flex flex-wrap items-center justify-between gap-3">
                                            <p class="text-sm text-red-800">
                                                Excluir a correção de <strong>{{ $correction->studentLabel() }}</strong>,
                                                incluindo a foto enviada?
                                            </p>
                                            <div class="flex gap-2">
                                                <button type="button" wire:click="cancelDeleteCorrection"
                                                        class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                                                    Cancelar
                                                </button>
                                                <button type="button" wire:click="deleteCorrection"
                                                        class="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700">
                                                    Confirmar exclusão
                                                </button>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            @endif
                        @endforeach
                    </tbody>
                </table>
            </div>
        @endif
    </section>
</div>
