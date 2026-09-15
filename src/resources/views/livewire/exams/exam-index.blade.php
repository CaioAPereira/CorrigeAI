<div class="space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
            <h1 class="text-2xl font-semibold tracking-tight">Provas</h1>
            <p class="mt-1 text-sm text-slate-500">
                Cadastre a prova e o gabarito, depois lance as fotos das folhas preenchidas.
            </p>
        </div>

        <div class="w-full sm:w-72">
            <label for="search" class="sr-only">Buscar prova</label>
            <input type="search" id="search" wire:model.live.debounce.300ms="search" placeholder="Buscar por nome..."
                   class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none">
        </div>
    </div>

    @if ($exams->isEmpty())
        <div class="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
            <p class="text-sm font-medium text-slate-700">
                {{ $search !== '' ? 'Nenhuma prova encontrada.' : 'Nenhuma prova cadastrada ainda.' }}
            </p>
            <p class="mt-1 text-sm text-slate-500">Comece criando a prova e informando o gabarito.</p>
            <a href="{{ route('exams.create') }}" wire:navigate
               class="mt-6 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700">
                Nova prova
            </a>
        </div>
    @else
        <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-slate-50 text-left text-xs font-medium tracking-wide text-slate-500 uppercase">
                        <tr>
                            <th class="px-6 py-3">Prova</th>
                            <th class="px-6 py-3">Aplicação</th>
                            <th class="px-6 py-3">Questões</th>
                            <th class="px-6 py-3">Gabarito</th>
                            <th class="px-6 py-3">Correções</th>
                            <th class="px-6 py-3 text-right">Ações</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        @foreach ($exams as $exam)
                            <tr class="hover:bg-slate-50">
                                <td class="px-6 py-4">
                                    <a href="{{ route('exams.show', $exam) }}" wire:navigate
                                       class="font-medium text-indigo-600 hover:text-indigo-800">
                                        {{ $exam->name }}
                                    </a>
                                    @if ($exam->description)
                                        <p class="mt-0.5 text-xs text-slate-500">{{ $exam->description }}</p>
                                    @endif
                                </td>
                                <td class="px-6 py-4 text-slate-600">
                                    {{ $exam->applied_on?->format('d/m/Y') ?? '—' }}
                                </td>
                                <td class="px-6 py-4 text-slate-600">
                                    {{ $exam->questions_count }} × {{ $exam->options_count }} alt.
                                </td>
                                <td class="px-6 py-4">
                                    @if ($exam->answer_key_items_count === $exam->questions_count)
                                        <span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
                                            Completo
                                        </span>
                                    @else
                                        <span class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                                            {{ $exam->answer_key_items_count }}/{{ $exam->questions_count }}
                                        </span>
                                    @endif
                                </td>
                                <td class="px-6 py-4 text-slate-600">{{ $exam->corrections_count }}</td>
                                <td class="px-6 py-4">
                                    <div class="flex items-center justify-end gap-3">
                                        <a href="{{ route('exams.show', $exam) }}" wire:navigate
                                           class="text-sm font-medium text-slate-600 hover:text-slate-900">Abrir</a>
                                        <a href="{{ route('exams.edit', $exam) }}" wire:navigate
                                           class="text-sm font-medium text-slate-600 hover:text-slate-900">Editar</a>
                                        <button type="button" wire:click="confirmDelete({{ $exam->id }})"
                                                class="text-sm font-medium text-red-600 hover:text-red-800">Excluir</button>
                                    </div>
                                </td>
                            </tr>

                            @if ($deletingId === $exam->id)
                                <tr class="bg-red-50">
                                    <td colspan="6" class="px-6 py-4">
                                        <div class="flex flex-wrap items-center justify-between gap-3">
                                            <p class="text-sm text-red-800">
                                                Excluir <strong>{{ $exam->name }}</strong> apaga também o gabarito e
                                                {{ $exam->corrections_count }} correção(ões). Essa ação não pode ser desfeita.
                                            </p>
                                            <div class="flex gap-2">
                                                <button type="button" wire:click="cancelDelete"
                                                        class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                                                    Cancelar
                                                </button>
                                                <button type="button" wire:click="delete"
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
        </div>

        @if ($exams->hasPages())
            <div>{{ $exams->links() }}</div>
        @endif
    @endif
</div>
