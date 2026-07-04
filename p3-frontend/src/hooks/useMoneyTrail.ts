import { useEffect, useState } from "react";
import { BASE_URL } from "../api/client";

export function useMoneyTrail(caseId?: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;

    setLoading(true);

    fetch(`${BASE_URL}/money-trail/${caseId}`)
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, [caseId]);

  return { data, loading };
}