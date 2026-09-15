<?php

namespace App\Livewire\Exams;

use App\Models\Exam;
use Livewire\Attributes\Layout;
use Livewire\Attributes\Title;
use Livewire\Attributes\Url;
use Livewire\Component;
use Livewire\WithPagination;

#[Layout('components.layout')]
#[Title('Provas')]
class ExamIndex extends Component
{
    use WithPagination;

    #[Url(as: 'q', except: '')]
    public string $search = '';

    public ?int $deletingId = null;

    public function updatedSearch(): void
    {
        $this->resetPage();
    }

    public function confirmDelete(int $examId): void
    {
        $this->deletingId = $examId;
    }

    public function cancelDelete(): void
    {
        $this->deletingId = null;
    }

    /**
     * Apagar a prova leva junto gabarito e correções (cascade no schema).
     * Por isso a exclusão passa por confirmação explícita na tela.
     */
    public function delete(): void
    {
        if ($this->deletingId === null) {
            return;
        }

        Exam::findOrFail($this->deletingId)->delete();

        $this->deletingId = null;

        session()->flash('status', 'Prova excluída.');
    }

    public function render()
    {
        $exams = Exam::query()
            ->withCount('corrections')
            ->withCount('answerKeyItems')
            ->when($this->search !== '', fn ($query) => $query->where('name', 'like', "%{$this->search}%"))
            ->latest('id')
            ->paginate(10);

        return view('livewire.exams.exam-index', [
            'exams' => $exams,
        ]);
    }
}
