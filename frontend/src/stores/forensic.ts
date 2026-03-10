import { defineStore } from "pinia";
import { ref } from "vue";

export interface InvestigateResult {
  address: string;
  risk_score: number;
  summary: string;
  evidence: string[];
}

export const useForensicStore = defineStore("forensic", () => {
  const investigationResult = ref<InvestigateResult | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function startInvestigation(address: string, chainId = 1) {
    isLoading.value = true;
    error.value = null;
    investigationResult.value = null;
    try {
      const response = await fetch("/api/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: address.trim(), chain_id: chainId }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${response.status}`);
      }
      investigationResult.value = (await response.json()) as InvestigateResult;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Investigation failed";
    } finally {
      isLoading.value = false;
    }
  }

  function clearResult() {
    investigationResult.value = null;
    error.value = null;
  }

  return {
    investigationResult,
    isLoading,
    error,
    startInvestigation,
    clearResult,
  };
});
