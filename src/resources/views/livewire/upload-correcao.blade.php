<div>
    <form wire:submit="save">
        <div>
            <label for="examId">Prova</label>
            <select id="examId" wire:model="examId">
                <option value="">Selecione</option>
                @foreach ($exams as $exam)
                    <option value="{{ $exam->id }}">{{ $exam->name }}</option>
                @endforeach
            </select>
            @error('examId') <span>{{ $message }}</span> @enderror
        </div>

        <div>
            <label for="image">Imagem do gabarito</label>
            <input type="file" id="image" wire:model="image">
            @error('image') <span>{{ $message }}</span> @enderror
        </div>

        <button type="submit">Corrigir</button>
    </form>

    @if ($correctAnswersCount !== null)
        <p>Acertos: {{ $correctAnswersCount }}</p>
    @endif
</div>
