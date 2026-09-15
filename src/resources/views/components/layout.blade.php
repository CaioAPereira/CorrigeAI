<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}" class="h-full">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <title>{{ $title ?? config('app.name', 'CorrigeAI') }}</title>

        @vite(['resources/css/app.css', 'resources/js/app.js'])
        @livewireStyles
    </head>
    <body class="h-full bg-slate-50 font-sans text-slate-900 antialiased">
        <div class="min-h-full">
            <header class="border-b border-slate-200 bg-white">
                <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
                    <a href="{{ route('exams.index') }}" wire:navigate class="flex items-center gap-3">
                        <span class="flex size-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
                            CA
                        </span>
                        <span>
                            <span class="block text-sm font-semibold tracking-tight">CorrigeAI</span>
                            <span class="block text-xs text-slate-500">Correção automática de gabaritos</span>
                        </span>
                    </a>

                    <nav class="flex items-center gap-1 text-sm">
                        <a href="{{ route('exams.index') }}" wire:navigate
                           @class([
                               'rounded-lg px-3 py-2 font-medium transition',
                               'bg-slate-100 text-slate-900' => request()->routeIs('exams.index'),
                               'text-slate-600 hover:bg-slate-50' => ! request()->routeIs('exams.index'),
                           ])>
                            Provas
                        </a>
                        <a href="{{ route('exams.create') }}" wire:navigate
                           class="rounded-lg bg-indigo-600 px-3 py-2 font-medium text-white shadow-sm transition hover:bg-indigo-700">
                            Nova prova
                        </a>
                    </nav>
                </div>
            </header>

            <main class="mx-auto max-w-6xl px-6 py-10">
                @if (session('status'))
                    <div class="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                        {{ session('status') }}
                    </div>
                @endif

                {{ $slot }}
            </main>
        </div>

        @livewireScripts
    </body>
</html>
