"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  AUTH_CHANGED_EVENT,
  cancelBatchAnalysis,
  createBatchAnalysis,
  getBatchAnalysis,
} from "@/lib/api-client";
import { BatchAnalysisCreate, BatchAnalysisResponse } from "@/types/api";

export const ACTIVE_BATCH_KEY = "jobshield_active_batch_id";

const POLL_INTERVAL_MS = 1500;
const RETRY_DELAYS_MS = [1500, 3000, 6000];

function getSavedActiveBatchId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(ACTIVE_BATCH_KEY);
  } catch {
    return null;
  }
}

function saveActiveBatchId(id: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(ACTIVE_BATCH_KEY, id);
  } catch {
    // ignore
  }
}

function clearSavedActiveBatchId(id?: string): void {
  if (typeof window === "undefined") return;
  try {
    if (id && localStorage.getItem(ACTIVE_BATCH_KEY) !== id) return;
    localStorage.removeItem(ACTIVE_BATCH_KEY);
  } catch {
    // ignore
  }
}

function getHttpStatus(error: unknown): number | undefined {
  return (error as { status?: number } | null)?.status;
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function isForbidden(error: unknown): boolean {
  const status = getHttpStatus(error);
  return status === 401 || status === 403;
}

function isRecoverable(error: unknown): boolean {
  const status = getHttpStatus(error);
  return status === undefined || status === 503;
}

function isBatchActive(batch: BatchAnalysisResponse): boolean {
  return (
    batch.status === "pending" ||
    batch.status === "processing" ||
    batch.items.some((item) => item.status === "processing")
  );
}

export function useBatchAnalysis(initialBatchId?: string | null) {
  const [batchId, setBatchId] = useState<string | null>(() =>
    initialBatchId !== undefined ? initialBatchId : getSavedActiveBatchId()
  );
  const [batch, setBatch] = useState<BatchAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deniedBatchId, setDeniedBatchId] = useState<string | null>(null);
  const [routeVersion, setRouteVersion] = useState(0);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [pollVersion, setPollVersion] = useState(0);

  const requestVersion = useRef(0);
  const cancelInFlightId = useRef<string | null>(null);
  const skipAutoLoadId = useRef<string | null>(null);
  const [prevInitialBatchId, setPrevInitialBatchId] = useState(initialBatchId);
  if (initialBatchId !== prevInitialBatchId) {
    setPrevInitialBatchId(initialBatchId);
    setRouteVersion((version) => version + 1);
    const nextBatchId = initialBatchId === undefined
      ? batchId ?? getSavedActiveBatchId()
      : initialBatchId;
    if (nextBatchId !== batchId) {
      setBatchId(nextBatchId);
      setBatch(null);
      setIsPolling(false);
      setIsLoading(false);
      setIsCancelling(false);
      setDeniedBatchId(null);
      setError(null);
    }
  }

  useLayoutEffect(() => {
    requestVersion.current += 1;
    skipAutoLoadId.current = null;
  }, [routeVersion]);

  const currentBatchId = batch?.id;

  useEffect(() => {
    if (!batchId || currentBatchId === batchId || deniedBatchId === batchId) return;
    if (skipAutoLoadId.current === batchId) {
      skipAutoLoadId.current = null;
      return;
    }

    let active = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const version = requestVersion.current;
    let retries = 0;
    setIsLoading(true);

    const load = async () => {
      if (!active || version !== requestVersion.current) return;
      try {
        const data = await getBatchAnalysis(batchId);
        if (!active || version !== requestVersion.current) return;
        setBatch(data);
        setError(null);
        if (isBatchActive(data)) {
          saveActiveBatchId(batchId);
          setIsPolling(true);
        } else {
          clearSavedActiveBatchId(batchId);
          setIsPolling(false);
        }
        setIsLoading(false);
      } catch (err: unknown) {
        if (!active || version !== requestVersion.current) return;
        if (isForbidden(err)) {
          clearSavedActiveBatchId(batchId);
          setBatch(null);
          setDeniedBatchId(batchId);
        }
        if (isRecoverable(err) && retries < RETRY_DELAYS_MS.length) {
          retries += 1;
          setError(`Lỗi kết nối, đang thử lại (${retries}/${RETRY_DELAYS_MS.length})...`);
          timer = setTimeout(load, RETRY_DELAYS_MS[retries - 1]);
          return;
        }
        setIsPolling(false);
        setError(getErrorMessage(err, "Không thể tải kết quả phân tích theo lô"));
        setIsLoading(false);
      }
    };

    void load();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [batchId, currentBatchId, deniedBatchId, reloadVersion, routeVersion]);

  useEffect(() => {
    if (!batchId || !isPolling) return;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const version = requestVersion.current;
    let retries = 0;

    const poll = async () => {
      if (!active || version !== requestVersion.current) return;
      try {
        const updated = await getBatchAnalysis(batchId);
        if (!active || version !== requestVersion.current) return;
        setBatch(updated);
        setError(null);
        retries = 0;
        if (isBatchActive(updated)) {
          saveActiveBatchId(batchId);
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          clearSavedActiveBatchId(batchId);
          setIsPolling(false);
        }
      } catch (err: unknown) {
        if (!active || version !== requestVersion.current) return;
        if (isForbidden(err)) {
          clearSavedActiveBatchId(batchId);
          setBatch(null);
          setDeniedBatchId(batchId);
        }
        if (isRecoverable(err) && retries < RETRY_DELAYS_MS.length) {
          retries += 1;
          setError(`Lỗi kết nối, đang thử lại (${retries}/${RETRY_DELAYS_MS.length})...`);
          timer = setTimeout(poll, RETRY_DELAYS_MS[retries - 1]);
          return;
        }
        setIsPolling(false);
        setError(getErrorMessage(err, "Lỗi khi cập nhật trạng thái phân tích theo lô"));
      }
    };

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [batchId, isPolling, pollVersion, routeVersion]);

  useEffect(() => {
    const handleAuthChange = () => {
      requestVersion.current += 1;
      cancelInFlightId.current = null;
      setBatch(null);
      setDeniedBatchId(null);
      setIsPolling(false);
      setIsLoading(false);
      setIsCancelling(false);
      setError(null);
      setReloadVersion((version) => version + 1);
    };
    window.addEventListener(AUTH_CHANGED_EVENT, handleAuthChange);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, handleAuthChange);
  }, []);

  const startBatch = useCallback(
    async (payload: BatchAnalysisCreate): Promise<BatchAnalysisResponse> => {
      const version = ++requestVersion.current;
      setIsLoading(true);
      setIsPolling(false);
      setError(null);
      try {
        const res = await createBatchAnalysis(payload);
        if (version !== requestVersion.current) return res;
        setBatchId(res.id);
        setBatch(res);
        if (isBatchActive(res)) {
          saveActiveBatchId(res.id);
          setIsPolling(true);
        } else {
          clearSavedActiveBatchId();
          setIsPolling(false);
        }
        setPollVersion((current) => current + 1);
        return res;
      } catch (err: unknown) {
        if (version === requestVersion.current) {
          setError(getErrorMessage(err, "Không thể bắt đầu phân tích theo lô"));
        }
        throw err;
      } finally {
        if (version === requestVersion.current) setIsLoading(false);
      }
    },
    []
  );

  const cancelBatch = useCallback(async (): Promise<void> => {
    const id = batchId;
    if (!id || cancelInFlightId.current === id) return;
    cancelInFlightId.current = id;
    const version = ++requestVersion.current;
    setIsLoading(true);
    setIsCancelling(true);
    setIsPolling(false);
    setError(null);
    try {
      const updated = await cancelBatchAnalysis(id);
      if (version !== requestVersion.current) return;
      setBatch(updated);
      const active = isBatchActive(updated);
      setIsPolling(active);
      if (active) saveActiveBatchId(id);
      else clearSavedActiveBatchId(id);
      setPollVersion((current) => current + 1);
    } catch (err: unknown) {
      if (version !== requestVersion.current) return;
      if (isForbidden(err)) {
        clearSavedActiveBatchId(id);
        setBatch(null);
        setDeniedBatchId(id);
      }
      setError(getErrorMessage(err, "Không thể hủy phân tích theo lô"));
      if (!isForbidden(err) && batch && isBatchActive(batch)) {
        setIsPolling(true);
        setPollVersion((current) => current + 1);
      }
    } finally {
      if (version === requestVersion.current) {
        setIsLoading(false);
        setIsCancelling(false);
      }
      if (cancelInFlightId.current === id) cancelInFlightId.current = null;
    }
  }, [batch, batchId]);

  const reset = useCallback((): void => {
    requestVersion.current += 1;
    skipAutoLoadId.current = null;
    setBatch(null);
    setBatchId(null);
    setError(null);
    setDeniedBatchId(null);
    setIsLoading(false);
    setIsPolling(false);
    setIsCancelling(false);
    clearSavedActiveBatchId();
  }, []);

  const loadBatch = useCallback(async (id: string): Promise<void> => {
    if (!id) return;
    const version = ++requestVersion.current;
    skipAutoLoadId.current = id;
    setDeniedBatchId(null);
    setBatchId(id);
    setIsLoading(true);
    setIsPolling(false);
    setError(null);
    try {
      const data = await getBatchAnalysis(id);
      if (version !== requestVersion.current) return;
      setBatch(data);
      const active = isBatchActive(data);
      setIsPolling(active);
      if (active) saveActiveBatchId(id);
      else clearSavedActiveBatchId(id);
      setPollVersion((current) => current + 1);
    } catch (err: unknown) {
      if (version !== requestVersion.current) return;
      if (isForbidden(err)) {
        clearSavedActiveBatchId(id);
        setBatch(null);
        setDeniedBatchId(id);
      }
      setError(getErrorMessage(err, "Không thể tải kết quả phân tích theo lô"));
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  }, []);

  return {
    batch,
    isLoading,
    isPolling,
    isCancelling,
    error,
    batchId,
    startBatch,
    cancelBatch,
    reset,
    loadBatch,
  };
}
