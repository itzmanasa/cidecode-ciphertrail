import { useQuery } from "@tanstack/react-query";
import { fetchCases } from "../api/endpoints";

export function useCases() {
  return useQuery({
    queryKey: ["cases"],
    queryFn: fetchCases,
    staleTime: 30_000,
  });
}
