"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getMyReport, getMyReports, submitReport } from "@/lib/api-client";
import { useSessionKey } from "@/hooks/use-session-key";
import { ReportCreate } from "@/types/api";

export function useSubmitReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReportCreate) => submitReport(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function useMyReports(page = 1, pageSize = 10) {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["reports", session, page, pageSize],
    queryFn: () => getMyReports(page, pageSize),
    enabled: Boolean(session),
  });
}

export function useMyReport(reportId: string) {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["reports", session, reportId],
    queryFn: () => getMyReport(reportId),
    enabled: Boolean(session && reportId),
  });
}
