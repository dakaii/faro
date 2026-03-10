<script setup lang="ts">
import { ref } from "vue";
import { useForensicStore } from "../stores/forensic";

const CHAINS = [
  { chainId: 1, name: "Ethereum" },
  { chainId: 8453, name: "Base" },
  { chainId: 42161, name: "Arbitrum One" },
] as const;

const store = useForensicStore();
const addressInput = ref("");
const selectedChainId = ref(1);

// Doc ingest (RAG)
const uploadFile = ref<HTMLInputElement | null>(null);
const uploadSource = ref("");
const uploadLoading = ref(false);
const uploadError = ref<string | null>(null);
const uploadResult = ref<{ ingested: number; source: string } | null>(null);

function riskBand(score: number): "low" | "medium" | "high" {
  if (score < 40) return "low";
  if (score < 70) return "medium";
  return "high";
}

function submit() {
  if (!addressInput.value.trim()) return;
  store.startInvestigation(addressInput.value, selectedChainId.value);
}

async function submitUpload() {
  const file = uploadFile.value?.files?.[0];
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
    uploadError.value = "Please select a PDF file.";
    return;
  }
  uploadError.value = null;
  uploadResult.value = null;
  uploadLoading.value = true;
  try {
    const form = new FormData();
    form.append("file", file);
    if (uploadSource.value.trim()) form.append("source", uploadSource.value.trim());
    const response = await fetch("/api/ingest-doc", {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? `Upload failed: ${response.status}`);
    }
    uploadResult.value = (await response.json()) as { ingested: number; source: string };
    if (uploadFile.value) uploadFile.value.value = "";
    uploadSource.value = "";
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : "Upload failed";
  } finally {
    uploadLoading.value = false;
  }
}
</script>

<template>
  <div class="space-y-8">
    <section class="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 class="font-mono text-sm font-semibold uppercase tracking-wider text-zinc-500">
        Investigate wallet
      </h2>
      <p class="mt-1 text-sm text-zinc-400">
        Enter an address to fetch on-chain data and get a risk report (Etherscan + Graph).
      </p>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <label class="flex items-center gap-2 text-sm text-zinc-400">
          <span>Chain</span>
          <select
            v-model.number="selectedChainId"
            class="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 font-mono text-sm text-zinc-100 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option v-for="c in CHAINS" :key="c.chainId" :value="c.chainId">
              {{ c.name }}
            </option>
          </select>
        </label>
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

    <section class="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 class="font-mono text-sm font-semibold uppercase tracking-wider text-zinc-500">
        Upload threat report
      </h2>
      <p class="mt-1 text-sm text-zinc-400">
        Add a PDF (e.g. REKT, Chainalysis report). It will be chunked, embedded, and used for RAG in investigations.
      </p>
      <div class="mt-4 flex flex-wrap items-end gap-3">
        <label class="flex flex-col gap-1 text-sm text-zinc-400">
          <span>PDF file</span>
          <input
            ref="uploadFile"
            type="file"
            accept=".pdf"
            class="font-mono text-sm text-zinc-300 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white file:hover:bg-cyan-500"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm text-zinc-400">
          <span>Source (optional)</span>
          <input
            v-model="uploadSource"
            type="text"
            placeholder="e.g. REKT Q1 2024"
            class="font-mono w-48 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
        </label>
        <button
          type="button"
          :disabled="uploadLoading"
          class="rounded-lg bg-zinc-700 px-5 py-2.5 font-medium text-white transition hover:bg-zinc-600 disabled:opacity-50"
          @click="submitUpload"
        >
          {{ uploadLoading ? "Uploading…" : "Upload" }}
        </button>
      </div>
      <p v-if="uploadError" class="mt-3 text-sm text-red-400">
        {{ uploadError }}
      </p>
      <p v-else-if="uploadResult" class="mt-3 text-sm text-zinc-400">
        Ingested {{ uploadResult.ingested }} chunk(s) from “{{ uploadResult.source }}”.
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
