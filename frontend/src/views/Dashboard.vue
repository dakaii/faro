<script setup lang="ts">
import { ref } from "vue";
import { useForensicStore } from "../stores/forensic";

const store = useForensicStore();
const addressInput = ref("");

function riskBand(score: number): "low" | "medium" | "high" {
  if (score < 40) return "low";
  if (score < 70) return "medium";
  return "high";
}

function submit() {
  if (!addressInput.value.trim()) return;
  store.startInvestigation(addressInput.value);
}
</script>

<template>
  <div class="space-y-8">
    <section class="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 class="font-mono text-sm font-semibold uppercase tracking-wider text-zinc-500">
        Investigate wallet
      </h2>
      <p class="mt-1 text-sm text-zinc-400">
        Enter an address to fetch on-chain data and get a risk report (Etherscan + GraphRAG placeholder).
      </p>
      <div class="mt-4 flex flex-wrap gap-3">
        <input
          v-model="addressInput"
          type="text"
          placeholder="0x..."
          class="font-mono w-full min-w-[20rem] rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          @keydown.enter="submit"
        />
        <button
          type="button"
          :disabled="store.isLoading"
          class="rounded-lg bg-cyan-600 px-5 py-2.5 font-medium text-white transition hover:bg-cyan-500 disabled:opacity-50"
          @click="submit"
        >
          {{ store.isLoading ? "Investigating…" : "Investigate" }}
        </button>
      </div>
      <p v-if="store.error" class="mt-3 text-sm text-red-400">
        {{ store.error }}
      </p>
    </section>

    <section
      v-if="store.investigationResult"
      class="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6"
    >
      <div class="flex items-center justify-between">
        <h2 class="font-mono text-sm font-semibold uppercase tracking-wider text-zinc-500">
          Report
        </h2>
        <button
          type="button"
          class="text-sm text-zinc-500 hover:text-zinc-300"
          @click="store.clearResult"
        >
          Clear
        </button>
      </div>
      <p class="mt-2 font-mono text-sm text-zinc-300 break-all">
        {{ store.investigationResult.address }}
      </p>
      <div class="mt-4 flex items-center gap-3">
        <span
          class="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium"
          :class="{
            'bg-risk-low/20 text-risk-low': riskBand(store.investigationResult.risk_score) === 'low',
            'bg-risk-medium/20 text-risk-medium': riskBand(store.investigationResult.risk_score) === 'medium',
            'bg-risk-high/20 text-risk-high': riskBand(store.investigationResult.risk_score) === 'high',
          }"
        >
          Risk score: {{ store.investigationResult.risk_score }}
        </span>
      </div>
      <p class="mt-4 text-sm text-zinc-400">
        {{ store.investigationResult.summary }}
      </p>
      <ul v-if="store.investigationResult.evidence.length" class="mt-4 list-inside list-disc space-y-1 text-sm text-zinc-500">
        <li v-for="(item, i) in store.investigationResult.evidence" :key="i">
          {{ item }}
        </li>
      </ul>
    </section>
  </div>
</template>
