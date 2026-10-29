"use client";

import { useSessionKey } from "@/hooks/use-session-key";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAdminEmployer,
  createPublicWarning,
  getAdminEmployers,
  getAdminWarnings,
  getAdminReport,
  getAdminReports,
  getAdminRules,
  getAdminStatistics,
  getPublicWarning,
  getPublicWarnings,
  moderateReport,
  supersedePublicWarning,
  updateAdminEmployer,
  updateAdminRule,
  withdrawPublicWarning,
} from "@/lib/api-client";
import {
  EmployerAdminCreate,
  EmployerAdminUpdate,
  ModerationActionCreate,
  PublicWarningCreate,
  PublicWarningSupersede,
  PublicWarningWithdraw,
  RiskIndicatorUpdateRequest,
} from "@/types/api";

export function useAdminReports(status?: string, page = 1, pageSize = 10) {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["admin", "reports", session, status, page, pageSize],
    queryFn: () => getAdminReports(status, page, pageSize),
    enabled: Boolean(session),
  });
}

export function useAdminReport(reportId: string) {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["admin", "reports", session, reportId],
    queryFn: () => getAdminReport(reportId),
    enabled: Boolean(session && reportId),
  });
}

export function useModerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      payload,
    }: {
      reportId: string;
      payload: ModerationActionCreate;
    }) => moderateReport(reportId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "reports"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "statistics"] });
    },
  });
}

export function useAdminEmployers(page = 1, pageSize = 10, search?: string) {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["admin", "employers", session, page, pageSize, search],
    queryFn: () => getAdminEmployers(page, pageSize, search),
    enabled: Boolean(session),
  });
}

export function useCreateAdminEmployer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: EmployerAdminCreate) => createAdminEmployer(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "employers"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "statistics"] });
    },
  });
}

export function useUpdateAdminEmployer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      employerId,
      payload,
    }: {
      employerId: string;
      payload: EmployerAdminUpdate;
    }) => updateAdminEmployer(employerId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "employers"] });
    },
  });
}

export function useAdminRules() {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["admin", "rules", session],
    queryFn: () => getAdminRules(),
    enabled: Boolean(session),
  });
}

export function useUpdateAdminRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      code,
      payload,
    }: {
      code: string;
      payload: RiskIndicatorUpdateRequest;
    }) => updateAdminRule(code, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "rules"] });
    },
  });
}

export function useAdminStats() {
  const session = useSessionKey();
  return useQuery({
    queryKey: ["admin", "statistics", session],
    queryFn: () => getAdminStatistics(),
    enabled: Boolean(session),
  });
}

export function usePublicWarnings(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["public", "warnings", page, pageSize],
    queryFn: () => getPublicWarnings(page, pageSize),
  });
}

export function usePublicWarning(warningId: string) {
  return useQuery({
    queryKey: ["public", "warnings", warningId],
    queryFn: () => getPublicWarning(warningId),
    enabled: Boolean(warningId),
  });
}

export function useCreatePublicWarning() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PublicWarningCreate) => createPublicWarning(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["public", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "statistics"] });
    },
  });
}

export function useSupersedePublicWarning() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      warningId,
      payload,
    }: {
      warningId: string;
      payload: PublicWarningSupersede;
    }) => supersedePublicWarning(warningId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["public", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "statistics"] });
    },
  });
}

export function useWithdrawPublicWarning() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      warningId,
      payload,
    }: {
      warningId: string;
      payload: PublicWarningWithdraw;
    }) => withdrawPublicWarning(warningId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["public", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "warnings"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "statistics"] });
    },
  });
}

export function useAdminWarnings(page = 1) {
  const session = useSessionKey();
  return useQuery({ queryKey: ["admin", "warnings", session, page], queryFn: () => getAdminWarnings(page), enabled: Boolean(session) });
}
