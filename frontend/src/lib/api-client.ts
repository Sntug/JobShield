import { AnalysisResponse, VerificationCreate, VerificationResponse } from "@/types/api";

const GUEST_TOKEN_KEY = "jobshield_guest_token";

export function getGuestToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(GUEST_TOKEN_KEY);
  } catch (err) {
    console.warn("sessionStorage không khả dụng:", err);
    return null;
  }
}

export function setGuestToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(GUEST_TOKEN_KEY, token);
  } catch (err) {
    console.error("Lỗi lưu token vào sessionStorage:", err);
    throw new Error(
      "Không thể lưu phiên làm việc vào trình duyệt (bộ nhớ tạm bị chặn hoặc đầy). Kết quả có thể không đọc lại được sau khi tải lại trang."
    );
  }
}

export function clearGuestToken(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(GUEST_TOKEN_KEY);
  } catch {
    // ignore
  }
}

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "";
}

export async function createAnalysis(text: string): Promise<AnalysisResponse> {
  const token = getGuestToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["X-Guest-Session-Token"] = token;
  }

  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyses`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text }),
  });

  if (response.status === 401) {
    // Không tự động xóa token ngầm trước khi người dùng xác nhận reset
    const errData = await response.json().catch(() => ({}));
    if (errData.detail === "SESSION_INVALID") {
      const err = new Error("Phiên khách đã hết hạn hoặc không hợp lệ. Vui lòng làm mới phiên để tiếp tục.");
      (err as unknown as { code: string }).code = "SESSION_INVALID";
      throw err;
    }
    throw new Error("Phiên làm việc không hợp lệ.");
  }

  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After") || "60";
    throw new Error(`Quá giới hạn tần suất yêu cầu. Vui lòng thử lại sau ${retryAfter} giây.`);
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message = Array.isArray(errData.detail)
      ? errData.detail.map((e: { msg?: string }) => e.msg).join(", ")
      : errData.detail || `Lỗi yêu cầu: ${response.status}`;
    throw new Error(message);
  }

  const data: AnalysisResponse = await response.json();
  if (data.guest_session_token) {
    setGuestToken(data.guest_session_token);
  }

  return data;
}

export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  const token = getGuestToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["X-Guest-Session-Token"] = token;
  }

  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyses/${id}`, {
    method: "GET",
    headers,
  });

  if (response.status === 404) {
    throw new Error("Không tìm thấy kết quả phân tích hoặc phiên làm việc đã hết hạn.");
  }

  if (!response.ok) {
    throw new Error(`Lỗi đọc kết quả: ${response.status}`);
  }

  return response.json();
}


export async function createVerification(payload: VerificationCreate, signal?: AbortSignal): Promise<VerificationResponse> {
  let response: Response;
  try {
    const timeout = AbortSignal.timeout(30_000);
    response = await fetch(`${getApiBaseUrl()}/api/v1/verifications`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload), credentials: "omit", cache: "no-store",
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Không thể kết nối kho nguồn hoặc yêu cầu đã hết thời gian. Vui lòng thử lại.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    let message = data?.detail?.message_vi || "Không thể hoàn tất xác minh. Vui lòng thử lại.";
    if (response.status === 429) {
      const seconds = Number.parseInt(response.headers.get("Retry-After") || "60", 10) || 60;
      message += ` Thử lại sau ${seconds} giây.`;
    }
    const labels: Record<string, string> = { company_name: "Tên công ty", tax_id: "Mã số thuế", contact_email: "Email", recruitment_website: "Website", social_channel_url: "Kênh mạng xã hội", bank_account: "Thông tin ngân hàng" };
    const invalidFields = Array.isArray(data?.detail?.errors) ? [...new Set<string>(data.detail.errors.map((error: { field?: string }) => labels[(error.field || "").split(".")[0]]).filter(Boolean))] : [];
    if (invalidFields.length) message += ` Kiểm tra: ${invalidFields.join(", ")}.`;
    throw new Error(message);
  }
  if (!data || !Array.isArray(data.field_checks) || !Array.isArray(data.matched_sources)) throw new Error("Phản hồi xác minh không hợp lệ. Vui lòng thử lại.");
  return data;
}
