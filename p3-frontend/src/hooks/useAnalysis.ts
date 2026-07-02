import { useQuery } from "@tanstack/react-query";
import { fetchAnalysis } from "../api/endpoints";

export function useAnalysis(caseId?: string) {
  return useQuery({
    queryKey: ["analysis", caseId],
    queryFn: () => fetchAnalysis(caseId as string),
    enabled: Boolean(caseId),
    staleTime: 60_000,
  });
}
