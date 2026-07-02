import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../api/endpoints";

export function useTransactions(caseId?: string) {
  return useQuery({
    queryKey: ["transactions", caseId],
    queryFn: () => fetchTransactions(caseId as string),
    enabled: Boolean(caseId),
    staleTime: 60_000,
  });
}
