import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ACTIVE_BATCH_KEY, useBatchAnalysis } from "@/hooks/use-batch-analysis";
import * as apiClient from "@/lib/api-client";
import {
  AUTH_CHANGED_EVENT,
  cancelBatchAnalysis,
  createBatchAnalysis,
  getBatchAnalysis,
} from "@/lib/api-client";
import { BatchAnalysisCreate, BatchAnalysisResponse } from "@/types/api";

const mockPendingBatch: BatchAnalysisResponse = {
  id: "batch-101",
  status: "pending",
  total_items: 2,
  processed_items: 0,
  created_at: "2026-11-03T10:00:00Z",
  items: [
    {
      id: "item-1",
      item_order: 1,
      input_type: "url",
      input_value: "https://example.com/job/1",
      status: "pending",
    },
    {
      id: "item-2",
      item_order: 2,
      input_type: "text",
      input_value: "Tuyển dụng nhân viên kế toán...",
      status: "pending",
    },
  ],
};

const mockProcessingBatch: BatchAnalysisResponse = {
  ...mockPendingBatch,
  status: "processing",
  processed_items: 1,
  items: [
    {
      ...mockPendingBatch.items[0],
      status: "success",
      analysis_id: "analysis-1",
    },
    {
      ...mockPendingBatch.items[1],
      status: "processing",
    },
  ],
};

const mockCompletedBatch: BatchAnalysisResponse = {
  ...mockPendingBatch,
  status: "completed",
  processed_items: 2,
  items: [
    {
      ...mockPendingBatch.items[0],
      status: "success",
      analysis_id: "analysis-1",
    },
    {
      ...mockPendingBatch.items[1],
      status: "success",
      analysis_id: "analysis-2",
    },
  ],
};

const mockFailedBatch: BatchAnalysisResponse = {
  ...mockPendingBatch,
  status: "failed",
  processed_items: 1,
};

const mockCancelledBatch: BatchAnalysisResponse = {
  ...mockProcessingBatch,
  status: "cancelled",
};

const mockCancelledSettledBatch: BatchAnalysisResponse = {
  ...mockCancelledBatch,
  processed_items: 2,
  items: [
    mockCancelledBatch.items[0],
    { ...mockCancelledBatch.items[1], status: "success" },
  ],
};

describe("useBatchAnalysis", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    localStorage.clear();
  });

  it("starts a batch and updates state and localStorage", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    vi.spyOn(apiClient, "getBatchAnalysis").mockResolvedValue(mockPendingBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    expect(result.current.batch).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isPolling).toBe(false);

    const payload: BatchAnalysisCreate = {
      items: [
        { type: "url", value: "https://example.com/job/1" },
        { type: "text", value: "Tuyển dụng..." },
      ],
    };

    let startPromise: Promise<BatchAnalysisResponse>;
    act(() => {
      startPromise = result.current.startBatch(payload);
    });

    await act(async () => {
      await startPromise;
    });

    expect(result.current.batch?.id).toBe("batch-101");
    expect(result.current.batch?.status).toBe("pending");
    expect(result.current.batchId).toBe("batch-101");
    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");
  });

  it("polls every 1500ms and stops when batch is completed", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    const getSpy = vi.spyOn(apiClient, "getBatchAnalysis");
    getSpy
      .mockResolvedValueOnce(mockProcessingBatch)
      .mockResolvedValueOnce(mockCompletedBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    // Advance 1500ms -> first poll returns mockProcessingBatch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(result.current.batch?.status).toBe("processing");
    expect(result.current.batch?.processed_items).toBe(1);
    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    // Advance another 1500ms -> second poll returns mockCompletedBatch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(result.current.batch?.status).toBe("completed");
    expect(result.current.batch?.processed_items).toBe(2);
    expect(result.current.isPolling).toBe(false);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();

    // Advance further -> no more calls since polling stopped
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it("stops polling and clears localStorage when status transitions to failed", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockResolvedValueOnce(mockFailedBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.isPolling).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(result.current.batch?.status).toBe("failed");
    expect(result.current.isPolling).toBe(false);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
  });

  it("cleans up timer on unmount and prevents further polling", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    const getSpy = vi.spyOn(apiClient, "getBatchAnalysis").mockResolvedValue(mockProcessingBatch);

    const { result, unmount } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.isPolling).toBe(true);

    // Unmount hook
    unmount();

    // Advance time past several intervals
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4500);
    });

    expect(getSpy).not.toHaveBeenCalled();
  });

  it("keeps polling a cancelled batch while an item is still processing", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockProcessingBatch);
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockResolvedValueOnce(mockCancelledSettledBatch);
    const cancelSpy = vi
      .spyOn(apiClient, "cancelBatchAnalysis")
      .mockResolvedValueOnce(mockCancelledBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    await act(async () => {
      await result.current.cancelBatch();
    });

    expect(cancelSpy).toHaveBeenCalledWith("batch-101");
    expect(result.current.batch?.status).toBe("cancelled");
    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(result.current.batch?.items[1].status).toBe("success");
    expect(result.current.isPolling).toBe(false);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
  });

  it("ignores a late response after switching to a different batch URL", async () => {
    let resolveFirst!: (batch: BatchAnalysisResponse) => void;
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce({ ...mockCompletedBatch, id: "batch-202" });

    const { result, rerender } = renderHook(
      ({ id }: { id: string | null }) => useBatchAnalysis(id),
      { initialProps: { id: "batch-101" } }
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    rerender({ id: "batch-202" });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(result.current.batch?.id).toBe("batch-202");

    await act(async () => {
      resolveFirst(mockFailedBatch);
      await Promise.resolve();
    });

    expect(result.current.batch?.id).toBe("batch-202");
    expect(result.current.batch?.status).toBe("completed");
  });

  it("retries a recoverable polling failure without dropping the active batch", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockRejectedValueOnce(new Error("Lỗi mạng kết nối"))
      .mockResolvedValueOnce(mockProcessingBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(result.current.isPolling).toBe(true);
    expect(result.current.error).toMatch(/thử lại/i);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(result.current.batch?.status).toBe("processing");
    expect(result.current.isPolling).toBe(true);
    expect(result.current.error).toBeNull();
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");
  });

  it("bounds transient retries, keeps recovery state, and exposes manual retry", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockRejectedValue(Object.assign(new Error("Service unavailable"), { status: 503 }));

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(12000);
    });

    expect(getSpy).toHaveBeenCalledTimes(4);
    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBe("Service unavailable");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    getSpy.mockResolvedValueOnce(mockProcessingBatch);
    await act(async () => {
      await result.current.loadBatch("batch-101");
    });

    expect(result.current.batch?.status).toBe("processing");
    expect(result.current.isPolling).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("does not overlap poll requests while a response is pending", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    let resolvePoll!: (batch: BatchAnalysisResponse) => void;
    const getSpy = vi.spyOn(apiClient, "getBatchAnalysis").mockImplementation(
      () => new Promise((resolve) => { resolvePoll = resolve; })
    );

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
      await vi.advanceTimersByTimeAsync(6000);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePoll(mockProcessingBatch);
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it("clears the cached batch immediately when access is forbidden", async () => {
    localStorage.setItem(ACTIVE_BATCH_KEY, "batch-101");
    const getSpy = vi.spyOn(apiClient, "getBatchAnalysis").mockRejectedValueOnce(
      Object.assign(new Error("Access denied"), { status: 403 })
    );

    const { result } = renderHook(() => useBatchAnalysis("batch-101"));

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getSpy).toHaveBeenCalledWith("batch-101");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBe("Access denied");
  });

  it("removes a forbidden batch from the screen and cache during polling", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockProcessingBatch);
    const getSpy = vi.spyOn(apiClient, "getBatchAnalysis").mockRejectedValueOnce(
      Object.assign(new Error("Forbidden"), { status: 403 })
    );
    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(result.current.batch).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBe("Forbidden");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000);
    });
    expect(getSpy).toHaveBeenCalledTimes(1);
  });

  it("removes a forbidden batch from the screen and cache when cancellation is rejected", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockProcessingBatch);
    vi.spyOn(apiClient, "cancelBatchAnalysis").mockRejectedValueOnce(
      Object.assign(new Error("Forbidden"), { status: 403 })
    );
    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });
    await act(async () => {
      await result.current.cancelBatch();
    });

    expect(result.current.batch).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.isCancelling).toBe(false);
    expect(result.current.error).toBe("Forbidden");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
  });

  it("clears cancellation state when auth changes during an in-flight cancel", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockProcessingBatch);
    let resolveCancel!: (batch: BatchAnalysisResponse) => void;
    vi.spyOn(apiClient, "cancelBatchAnalysis").mockImplementationOnce(
      () => new Promise((resolve) => { resolveCancel = resolve; })
    );
    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });
    act(() => {
      void result.current.cancelBatch();
    });

    expect(result.current.isCancelling).toBe(true);

    act(() => {
      window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
    });

    expect(result.current.isCancelling).toBe(false);

    await act(async () => {
      resolveCancel(mockCancelledBatch);
      await Promise.resolve();
    });

    expect(result.current.batch).toBeNull();
    expect(result.current.isCancelling).toBe(false);
  });

  it("preserves the active batch when switching to a route without batch_id", async () => {
    localStorage.setItem(ACTIVE_BATCH_KEY, "batch-101");
    vi.spyOn(apiClient, "getBatchAnalysis").mockResolvedValueOnce(mockProcessingBatch);
    const { result, rerender } = renderHook(
      ({ id }: { id: string | undefined }) => useBatchAnalysis(id),
      { initialProps: { id: "batch-101" as string | undefined } }
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current.batch?.id).toBe("batch-101");

    rerender({ id: undefined });

    expect(result.current.batch?.id).toBe("batch-101");
    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");
  });

  it("loads batch by id and starts polling if pending", async () => {
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockResolvedValueOnce(mockProcessingBatch)
      .mockResolvedValueOnce(mockCompletedBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.loadBatch("batch-101");
    });

    expect(getSpy).toHaveBeenCalledWith("batch-101");
    expect(result.current.batchId).toBe("batch-101");
    expect(result.current.batch?.status).toBe("processing");
    expect(result.current.isPolling).toBe(true);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(result.current.batch?.status).toBe("completed");
    expect(result.current.isPolling).toBe(false);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
  });

  it("resets state and clears localStorage", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.batchId).toBe("batch-101");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");

    act(() => {
      result.current.reset();
    });

    expect(result.current.batch).toBeNull();
    expect(result.current.batchId).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull();
  });

  it("resumes batch on mount if active batch ID exists in localStorage", async () => {
    localStorage.setItem(ACTIVE_BATCH_KEY, "batch-101");
    const getSpy = vi
      .spyOn(apiClient, "getBatchAnalysis")
      .mockResolvedValueOnce(mockProcessingBatch);

    let hookResult!: ReturnType<typeof renderHook<ReturnType<typeof useBatchAnalysis>, unknown>>;
    await act(async () => {
      hookResult = renderHook(() => useBatchAnalysis());
    });

    expect(hookResult.result.current.batchId).toBe("batch-101");
    expect(hookResult.result.current.batch?.status).toBe("processing");
    expect(hookResult.result.current.isPolling).toBe(true);
    expect(getSpy).toHaveBeenCalledWith("batch-101");
  });

  it("stops polling after a non-recoverable GET error and keeps the active batch cached", async () => {
    vi.spyOn(apiClient, "createBatchAnalysis").mockResolvedValueOnce(mockPendingBatch);
    vi.spyOn(apiClient, "getBatchAnalysis").mockRejectedValueOnce(
      Object.assign(new Error("Bad request"), { status: 400 })
    );

    const { result } = renderHook(() => useBatchAnalysis());

    await act(async () => {
      await result.current.startBatch({
        items: [{ type: "url", value: "https://example.com/job/1" }],
      });
    });

    expect(result.current.isPolling).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBe("Bad request");
    expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBe("batch-101");
  });
});

describe("API client batch analysis functions", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("createBatchAnalysis sends guest token and stores new guest session token", async () => {
    sessionStorage.setItem("jobshield_guest_token", "guest-token-123");

    const fetchSpy = vi.fn(async (_url: string, options: RequestInit) => {
      const headers = new Headers(options.headers);
      expect(headers.get("X-Guest-Session-Token")).toBe("guest-token-123");
      expect(headers.get("Content-Type")).toBe("application/json");

      return new Response(
        JSON.stringify({
          ...mockPendingBatch,
          guest_session_token: "new-guest-token-456",
        }),
        { status: 200 }
      );
    });
    vi.stubGlobal("fetch", fetchSpy);

    const res = await createBatchAnalysis({
      items: [{ type: "url", value: "https://example.com/test" }],
      use_ai: true,
      ai_consent: true,
    });

    expect(res.id).toBe("batch-101");
    expect(sessionStorage.getItem("jobshield_guest_token")).toBe("new-guest-token-456");
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/batches/analyses"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("clears the unchanged guest token after a definitive expired-session response", async () => {
    sessionStorage.setItem("jobshield_guest_token", "expired-guest-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, options: RequestInit) => {
        expect(new Headers(options.headers).get("X-Guest-Session-Token")).toBe(
          "expired-guest-token"
        );
        return new Response(JSON.stringify({ detail: "SESSION_INVALID" }), { status: 401 });
      })
    );

    await expect(
      createBatchAnalysis({ items: [{ type: "text", value: "Tin tuyển dụng" }] })
    ).rejects.toMatchObject({
      code: "SESSION_INVALID",
      message: expect.stringMatching(/gửi lại yêu cầu/i),
    });
    expect(sessionStorage.getItem("jobshield_guest_token")).toBeNull();
  });

  it("preserves a newer guest token when an old batch create gets SESSION_INVALID", async () => {
    sessionStorage.setItem("jobshield_guest_token", "expired-guest-token");
    let resolveResponse!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    })));

    const createRequest = createBatchAnalysis({
      items: [{ type: "text", value: "Tin tuyển dụng" }],
    });
    await Promise.resolve();
    sessionStorage.setItem("jobshield_guest_token", "new-guest-token");
    resolveResponse(new Response(JSON.stringify({ detail: "SESSION_INVALID" }), { status: 401 }));

    await expect(createRequest).rejects.toMatchObject({ code: "SESSION_INVALID" });
    expect(sessionStorage.getItem("jobshield_guest_token")).toBe("new-guest-token");
  });

  it("does not clear a guest token when a batch GET is forbidden", async () => {
    sessionStorage.setItem("jobshield_guest_token", "current-guest-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }))
    );

    await expect(getBatchAnalysis("batch-owned-by-someone-else")).rejects.toMatchObject({
      status: 403,
    });
    expect(sessionStorage.getItem("jobshield_guest_token")).toBe("current-guest-token");
  });

  it("stores a new guest credential from batch creation and uses it to read the batch", async () => {
    const fetchSpy = vi
      .fn()
      .mockImplementationOnce(async (_url: string, options: RequestInit) => {
        const headers = new Headers(options.headers);
        expect(headers.has("X-Guest-Session-Token")).toBe(false);
        return new Response(
          JSON.stringify({ ...mockPendingBatch, guest_session_token: "guest-created-by-batch" }),
          { status: 201 }
        );
      })
      .mockImplementationOnce(async (_url: string, options: RequestInit) => {
        const headers = new Headers(options.headers);
        expect(headers.get("X-Guest-Session-Token")).toBe("guest-created-by-batch");
        return new Response(JSON.stringify(mockPendingBatch), { status: 200 });
      });
    vi.stubGlobal("fetch", fetchSpy);

    await createBatchAnalysis({
      items: [{ type: "text", value: "Tuyển kỹ sư phần mềm" }],
    });
    expect(sessionStorage.getItem("jobshield_guest_token")).toBe("guest-created-by-batch");

    await getBatchAnalysis("batch-101");
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("does not apply a late guest credential after the current auth context changes", async () => {
    let resolveResponse!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { resolveResponse = resolve; })));

    const createRequest = createBatchAnalysis({
      items: [{ type: "text", value: "Tin tuyển dụng" }],
    });
    await Promise.resolve();
    sessionStorage.setItem("jobshield_auth_token", "new-account-session");
    resolveResponse(
      new Response(
        JSON.stringify({ ...mockPendingBatch, guest_session_token: "stale-guest-token" }),
        { status: 201 }
      )
    );

    await createRequest;
    expect(sessionStorage.getItem("jobshield_auth_token")).toBe("new-account-session");
    expect(sessionStorage.getItem("jobshield_guest_token")).toBeNull();
  });

  it("createBatchAnalysis sends Authorization bearer token when user is signed in", async () => {
    sessionStorage.setItem("jobshield_auth_token", "bearer-token-abc");

    const fetchSpy = vi.fn(async (_url: string, options: RequestInit) => {
      const headers = new Headers(options.headers);
      expect(headers.get("Authorization")).toBe("Bearer bearer-token-abc");
      return new Response(JSON.stringify(mockPendingBatch), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const res = await createBatchAnalysis({
      items: [{ type: "text", value: "Tuyển kỹ sư phần mềm" }],
    });

    expect(res.id).toBe("batch-101");
  });

  it("getBatchAnalysis sends correct headers and returns batch data", async () => {
    sessionStorage.setItem("jobshield_guest_token", "guest-token-123");

    const fetchSpy = vi.fn(async (url: string, options: RequestInit) => {
      expect(url).toContain("/api/v1/batches/analyses/batch-101");
      const headers = new Headers(options.headers);
      expect(headers.get("X-Guest-Session-Token")).toBe("guest-token-123");
      return new Response(JSON.stringify(mockProcessingBatch), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const res = await getBatchAnalysis("batch-101");
    expect(res.status).toBe("processing");
    expect(res.processed_items).toBe(1);
  });

  it("getBatchAnalysis throws 404 error when not found", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Not found", { status: 404 })));

    await expect(getBatchAnalysis("unknown-id")).rejects.toThrow(
      "Không tìm thấy kết quả phân tích theo lô hoặc phiên làm việc đã hết hạn."
    );
  });

  it("preserves the HTTP status on batch GET errors for retry decisions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Unavailable" }), { status: 503 }))
    );

    await expect(getBatchAnalysis("batch-101")).rejects.toMatchObject({ status: 503 });
  });

  it("cancelBatchAnalysis sends POST to cancel endpoint and returns updated batch", async () => {
    const fetchSpy = vi.fn(async (url: string, options: RequestInit) => {
      expect(url).toContain("/api/v1/batches/analyses/batch-101/cancel");
      expect(options.method).toBe("POST");
      return new Response(JSON.stringify(mockCancelledBatch), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const res = await cancelBatchAnalysis("batch-101");
    expect(res.status).toBe("cancelled");
  });
});
