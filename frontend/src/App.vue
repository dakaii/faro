<script setup lang="ts">
import Dashboard from "./views/Dashboard.vue";
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-zinc-800 bg-zinc-900/80 px-6 py-4">
      <h1 class="font-mono text-lg font-semibold tracking-tight text-zinc-100">
        Faro
      </h1>
      <p class="mt-0.5 text-sm text-zinc-500">
        Blockchain forensic investigator – wallet risk report
      </p>
    </header>
    <main class="mx-auto max-w-4xl px-6 py-8">
      <Dashboard />
    </main>
  </div>
</template>
