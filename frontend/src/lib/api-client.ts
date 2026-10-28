import {
  AnalysisListResponse,
  AnalysisResponse,
  ClaimGuestResponse,
  ExtractionResponse,
  SavedAnalysisListResponse,
  TokenResponse,
  User,
  UserStats,
  VerificationCreate,
  VerificationResponse,
} from "@/types/api";

const GUEST_TOKEN_KEY = "jobshield_guest_token";
const AUTH_TOKEN_KEY = "jobshield_auth_token";
export const AUTH_CHANGED_EVENT = "jobshield-auth-changed";

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
      "Không thể lưu phiên làm việc vào trình duyệt (bộ nhớ tạm bị chặn hoặc đầy)."
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

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(AUTH_TOKEN_KEY);
  } catch (err) {
    console.warn("sessionStorage không khả dụng:", err);
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token);
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
  } catch (err) {
    console.error("Lỗi lưu auth token vào sessionStorage:", err);
    throw new Error("Không thể lưu token xác thực vào trình duyệt.");
  }
}

export function clearAuthToken(expectedToken: string | null = getAuthToken()): void {
  if (typeof window === "undefined") return;
  if (getAuthToken() !== expectedToken) return;
  try {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // ignore
  }
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "";
}

async function authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(url, { ...options, headers, cache: "no-store" });
  // A response from an earlier account must never invalidate the current session.
  if (response.status === 401 && token) clearAuthToken(token);
  return response;
}

function apiErrorMessage(data: unknown, fallback: string): string {
  const detail = data && typeof data === "object" && "detail" in data ? data.detail : null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: unknown }) => typeof item?.msg === "string" ? item.msg : "")
      .filter(Boolean).join("; ") || fallback;
  }
  if (detail && typeof detail === "object" && "message_vi" in detail && typeof detail.message_vi === "string") {
    return detail.message_vi;
  }
  return fallback;
}

export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<TokenResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, `Đăng ký thất bại (${response.status})`));
  }

  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, `Đăng nhập thất bại (${response.status})`));
  }

  return data;
}

export async function logout(): Promise<void> {
  const token = getAuthToken();
  try {
    await authenticatedFetch(`${getApiBaseUrl()}/api/v1/auth/logout`, {
      method: "POST",
    });
  } finally {
    clearAuthToken(token);
  }
}

export async function getMe(): Promise<User> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/users/me`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Không thể tải thông tin tài khoản.");
  }

  return response.json();
}

export async function updateProfile(fullName: string): Promise<User> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/users/me`, {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, "Cập nhật hồ sơ thất bại."));
  }
  return data;
}

export async function changePassword(
  oldPassword: string,
  newPassword: string
): Promise<void> {
  const token = getAuthToken();
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/users/me/password`, {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, "Đổi mật khẩu thất bại."));
  }
  clearAuthToken(token);
}

export async function getUserStats(): Promise<UserStats> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/users/me/stats`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Không thể tải thống kê cá nhân.");
  }
  return response.json();
}

export async function claimGuestAnalyses(
  guestToken: string
): Promise<ClaimGuestResponse> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/auth/claim-guest`, {
    method: "POST",
    body: JSON.stringify({ guest_session_token: guestToken }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, "Không thể nhận quyền phân tích khách."));
  }
  clearGuestToken();
  return data;
}

export async function listAnalyses(
  page: number = 1,
  pageSize: number = 10,
  isSaved?: boolean
): Promise<AnalysisListResponse> {
  let url = `${getApiBaseUrl()}/api/v1/analyses?page=${page}&page_size=${pageSize}`;
  if (isSaved !== undefined) {
    url += `&is_saved=${isSaved}`;
  }

  const response = await authenticatedFetch(url, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Không thể tải lịch sử phân tích.");
  }
  return response.json();
}

export async function deleteAnalysis(id: string): Promise<void> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/analyses/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Không thể xóa kết quả phân tích.");
  }
}

export async function saveAnalysis(id: string): Promise<void> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/saved-analyses/${id}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Không thể lưu kết quả phân tích.");
  }
}

export async function unsaveAnalysis(id: string): Promise<void> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/saved-analyses/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Không thể bỏ lưu kết quả phân tích.");
  }
}

export async function listSavedAnalyses(
  page: number = 1,
  pageSize: number = 10
): Promise<SavedAnalysisListResponse> {
  const url = `${getApiBaseUrl()}/api/v1/saved-analyses?page=${page}&page_size=${pageSize}`;
  const response = await authenticatedFetch(url, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Không thể tải danh sách bài đã lưu.");
  }
  return response.json();
}

export async function createAnalysis(text: string): Promise<AnalysisResponse> {
  const authToken = getAuthToken();
  const guestToken = getGuestToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  } else if (guestToken) {
    headers["X-Guest-Session-Token"] = guestToken;
  }

  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/analyses`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text }),
  });

  if (response.status === 401) {
    const errData = await response.json().catch(() => ({}));
    if (errData.detail === "SESSION_INVALID") {
      const err = new Error(
        "Phiên khách đã hết hạn hoặc không hợp lệ. Vui lòng làm mới phiên để tiếp tục."
      );
      (err as unknown as { code: string }).code = "SESSION_INVALID";
      throw err;
    }
    throw new Error("Phiên làm việc không hợp lệ.");
  }

  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After") || "60";
    throw new Error(
      `Quá giới hạn tần suất yêu cầu. Vui lòng thử lại sau ${retryAfter} giây.`
    );
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(errData, `Lỗi yêu cầu: ${response.status}`));
  }

  const data: AnalysisResponse = await response.json();
  if (data.guest_session_token) {
    setGuestToken(data.guest_session_token);
  }

  return data;
}

export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  const authToken = getAuthToken();
  const guestToken = getGuestToken();

  const headers: Record<string, string> = {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  } else if (guestToken) {
    headers["X-Guest-Session-Token"] = guestToken;
  }

  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/analyses/${id}`, {
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

export async function createVerification(
  payload: VerificationCreate,
  signal?: AbortSignal
): Promise<VerificationResponse> {
  let response: Response;
  try {
    const timeout = AbortSignal.timeout(30_000);
    response = await fetch(`${getApiBaseUrl()}/api/v1/verifications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "same-origin",
      cache: "no-store",
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(
      "Không thể kết nối kho nguồn hoặc yêu cầu đã hết thời gian. Vui lòng thử lại."
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    let message =
      data?.detail?.message_vi || "Không thể hoàn tất xác minh. Vui lòng thử lại.";
    if (response.status === 429) {
      const seconds =
        Number.parseInt(response.headers.get("Retry-After") || "60", 10) || 60;
      message += ` Thử lại sau ${seconds} giây.`;
    }
    const labels: Record<string, string> = {
      company_name: "Tên công ty",
      tax_id: "Mã số thuế",
      contact_email: "Email",
      recruitment_website: "Website",
      social_channel_url: "Kênh mạng xã hội",
      bank_account: "Thông tin ngân hàng",
    };
    const invalidFields = Array.isArray(data?.detail?.errors)
      ? [
          ...new Set<string>(
            data.detail.errors
              .map((error: { field?: string }) => labels[(error.field || "").split(".")[0]])
              .filter(Boolean)
          ),
        ]
      : [];
    if (invalidFields.length) message += ` Kiểm tra: ${invalidFields.join(", ")}.`;
    throw new Error(message);
  }
  if (!data || !Array.isArray(data.field_checks) || !Array.isArray(data.matched_sources)) {
    throw new Error("Phản hồi xác minh không hợp lệ. Vui lòng thử lại.");
  }
  return data;
}

export async function extractFromUrl(url: string): Promise<ExtractionResponse> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/extractions/url`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
  });

  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After") || "60";
    throw new Error(`Quá giới hạn tần suất yêu cầu. Vui lòng thử lại sau ${retryAfter} giây.`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const msg = data?.detail || "Không thể trích xuất nội dung từ liên kết. Vui lòng thử lại hoặc dán văn bản trực tiếp.";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  return data as ExtractionResponse;
}

export async function extractFromImage(file: File): Promise<ExtractionResponse> {
  if (file.size > 5 * 1024 * 1024) {
    throw new Error("Kích thước tệp vượt quá giới hạn tối đa 5MB.");
  }
  const allowed = ["image/png", "image/jpeg", "image/webp"];
  if (file.type && !allowed.includes(file.type.toLowerCase())) {
    throw new Error("Định dạng tệp không được hỗ trợ. Chỉ chấp nhận ảnh PNG, JPEG hoặc WebP.");
  }

  const response = await authenticatedFetch(`${getApiBaseUrl()}/api/v1/extractions/image`, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "image/png",
      "X-Filename": encodeURIComponent(file.name),
    },
    body: file,
  });

  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After") || "60";
    throw new Error(`Quá giới hạn tần suất yêu cầu. Vui lòng thử lại sau ${retryAfter} giây.`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const msg = data?.detail || "Không thể trích xuất văn bản từ ảnh. Vui lòng thử lại hoặc dán văn bản trực tiếp.";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  return data as ExtractionResponse;
}
