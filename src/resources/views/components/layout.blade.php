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
                <div class="mx-auto flex max-w-5xl items-center gap-3 px-6 py-4">
                    <span class="flex size-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
                        CA
                    </span>
                    <div>
                        <p class="text-sm font-semibold tracking-tight">CorrigeAI</p>
                        <p class="text-xs text-slate-500">Correção automática de gabaritos</p>
                    </div>
                </div>
            </header>

            <main class="mx-auto max-w-5xl px-6 py-10">
                {{ $slot }}
            </main>
        </div>

        @livewireScripts
    </body>
</html>
