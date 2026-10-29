import { expect, test } from "./fixtures";
import path from "node:path";

test.describe("Các phương thức nhập tin tuyển dụng (/analyze - R3)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByRole("heading", { level: 1, name: "Phân tích tin tuyển dụng" })).toBeVisible();
  });

  test("chuyển đổi giữa các tab nhập liệu: Văn bản, Hình ảnh, Liên kết", async ({ page }) => {
    const tabText = page.getByRole("tab", { name: "Văn bản" });
    const tabImage = page.getByRole("tab", { name: /Hình ảnh/i });
    const tabUrl = page.getByRole("tab", { name: /Liên kết/i });

    await expect(tabText).toHaveAttribute("aria-selected", "true");

    await tabImage.click();
    await expect(tabImage).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(/Chọn ảnh chụp tin tuyển dụng/i)).toBeVisible();

    await tabUrl.click();
    await expect(tabUrl).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(/Đường dẫn tin tuyển dụng công khai/i)).toBeVisible();

    await tabText.click();
    await expect(tabText).toHaveAttribute("aria-selected", "true");
  });

  test("trích xuất từ URL thành công, cho phép sửa văn bản và phân tích", async ({ page }) => {
    // 1. Chuyển sang tab URL
    await page.getByRole("tab", { name: /Liên kết/i }).click();

    // Mock API URL extraction thành công
    await page.route("**/api/v1/extractions/url", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "req-e2e-url-1",
          success: true,
          source_type: "url",
          text: "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. Email: tuyendung@mau-a.example.",
          failure_vi: null,
          source_name: "https://tin-demo.example/complete",
        }),
      });
    });

    const urlInput = page.getByPlaceholder(/https:\/\/tuyendung\.example/i);
    await urlInput.fill("https://tin-demo.example/complete");

    const extractBtn = page.getByRole("button", { name: /Lấy nội dung từ liên kết/i });
    await extractBtn.click();

    // 2. Đọc thành công: văn bản xuất hiện trong textarea kèm thông báo
    const textarea = page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i);
    await expect(textarea).toHaveValue(
      "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. Email: tuyendung@mau-a.example."
    );
    await expect(page.getByText(/Đã trích xuất nội dung từ liên kết/i)).toBeVisible();

    // 3. Sửa văn bản: bổ sung yêu cầu không thu phí
    await textarea.fill(
      "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. Email: tuyendung@mau-a.example. Không thu phí hoặc đặt cọc."
    );

    // 4. Submit phân tích với văn bản đã sửa
    const submitBtn = page.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    await expect(submitBtn).toBeEnabled();
  });

  test("trích xuất từ ảnh thành công và hiển thị trong khung chỉnh sửa", async ({ page }) => {
    await page.getByRole("tab", { name: /Hình ảnh/i }).click();

    await page.route("**/api/v1/extractions/image", async (route) => {
      expect(route.request().headers()["content-type"]).toBe("image/png");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "req-e2e-img-1",
          success: true,
          source_type: "image",
          text: "Công ty Mẫu A (DEMO) tuyển Lập trình viên Backend. Lương: 15–20 triệu. Email: tuyendung@mau-a.example.",
          failure_vi: null,
          source_name: "job-ad.png",
          confidence: 0.95,
        }),
      });
    });

    // Tạo file ảnh giả lập
    const buffer = Buffer.from(
      "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082",
      "hex"
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.locator("#recruitment-image-file").click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "job-ad.png",
      mimeType: "image/png",
      buffer,
    });

    await page.getByRole("button", { name: /Trích xuất văn bản từ ảnh/i }).click();

    const textarea = page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i);
    await expect(textarea).toHaveValue(
      "Công ty Mẫu A (DEMO) tuyển Lập trình viên Backend. Lương: 15–20 triệu. Email: tuyendung@mau-a.example."
    );
    await expect(page.getByText(/Đã trích xuất văn bản từ ảnh thành công/i)).toBeVisible();
  });

  test("URL sai không ngăn phân tích văn bản dán thủ công", async ({ page }) => {
    await page.getByRole("tab", { name: /Liên kết/i }).click();
    await page.route("**/api/v1/extractions/url", route => route.fulfill({
      status: 422, contentType: "application/json", body: JSON.stringify({ detail: "URL không hợp lệ." }),
    }));
    await page.route("**/api/v1/analyses", route => route.fulfill({
      status: 429, contentType: "application/json", body: JSON.stringify({ detail: "Test reached analysis API" }),
    }));
    await page.getByLabel("Đường dẫn tin tuyển dụng công khai").fill("not-a-url");
    await page.getByRole("button", { name: /Lấy nội dung từ liên kết/i }).click();
    await expect(page.locator("form").getByRole("alert")).toContainText("URL không hợp lệ.");
    const text = "Nội dung tin tuyển dụng dán thủ công sau khi URL không hợp lệ.";
    await page.getByLabel("Nội dung tin tuyển dụng cần phân tích").fill(text);
    const submitted = page.waitForRequest(request => request.url().endsWith("/api/v1/analyses") && request.method() === "POST", { timeout: 2000 });
    await page.getByRole("button", { name: /Phân tích tin tuyển dụng/i }).click();
    expect((await submitted).postDataJSON()).toEqual({ text });
  });

  test("ảnh thật qua CORS và OCR -> sửa văn bản -> phân tích bằng API thật", async ({ page }) => {
    await page.getByRole("tab", { name: /Hình ảnh/i }).click();
    await page.locator("#recruitment-image-file").setInputFiles(
      path.resolve(process.cwd(), "../backend/tests/fixtures/r3-job.png")
    );
    const direct = await page.evaluate(async target => {
      const input = document.querySelector<HTMLInputElement>("#recruitment-image-file");
      const file = input!.files![0];
      const response = await fetch(`${target}/api/v1/extractions/image`, {
        method: "POST", headers: { "Content-Type": file.type, "X-Filename": file.name }, body: file,
      });
      return { status: response.status, body: await response.json() };
    }, process.env.API_PROXY_TARGET || "http://127.0.0.1:8000");
    expect(direct.status).toBe(200);
    expect(direct.body.success).toBe(true);
    expect(direct.body.text).toContain("Backend");

    await page.getByRole("button", { name: /Trích xuất văn bản từ ảnh/i }).click();
    const textarea = page.getByLabel("Nội dung tin tuyển dụng cần phân tích");
    await expect(textarea).toHaveValue(/Backend/, { timeout: 15000 });
    await textarea.fill("Công ty ABC tuyển lập trình viên Backend. Lương 20 triệu đồng/tháng. Không thu phí hoặc đặt cọc.");
    const analyzed = page.waitForResponse(response => response.url().endsWith("/api/v1/analyses") && response.request().method() === "POST");
    await page.getByRole("button", { name: /Phân tích tin tuyển dụng/i }).click();
    expect((await analyzed).status()).toBe(201);
    await expect(page).toHaveURL(/\?id=/);
    await expect(page.getByText(/Mức độ:/)).toBeVisible();
  });

  test("xử lý ca lỗi OCR (ảnh mờ) và cho phép người dùng tự dán văn bản", async ({ page }) => {
    await page.getByRole("tab", { name: /Hình ảnh/i }).click();

    await page.route("**/api/v1/extractions/image", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "req-e2e-blurry",
          success: false,
          source_type: "image",
          text: null,
          failure_vi: "Ảnh DEMO bị mờ, không đọc được chữ.",
        }),
      });
    });

    const buffer = Buffer.from("blurry image content");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.locator("#recruitment-image-file").click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "blurry.png",
      mimeType: "image/png",
      buffer,
    });

    await page.getByRole("button", { name: /Trích xuất văn bản từ ảnh/i }).click();

    // Hiển thị lỗi rõ ràng
    await expect(page.locator("form").getByRole("alert")).toContainText("Ảnh DEMO bị mờ, không đọc được chữ.");
    await expect(
      page.getByText(/Bạn có thể nhập hoặc dán toàn bộ nội dung tin tuyển dụng vào khung bên dưới/i)
    ).toBeVisible();

    // Người dùng dán văn bản vào textarea
    const textarea = page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i);
    await textarea.fill("Nội dung tin tuyển dụng nhập tay sau khi ảnh bị mờ.");
    await expect(page.getByRole("button", { name: /Phân tích tin tuyển dụng/i })).toBeEnabled();
  });

  test("xử lý ca URL bị chặn / yêu cầu đăng nhập và lỗi timeout", async ({ page }) => {
    await page.getByRole("tab", { name: /Liên kết/i }).click();

    // 1. URL bị chặn (url_blocked)
    await page.route("**/api/v1/extractions/url", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "req-e2e-blocked",
          success: false,
          source_type: "url",
          text: null,
          failure_vi: "Trang DEMO yêu cầu đăng nhập; không trích xuất nội dung.",
        }),
      });
    });

    const urlInput = page.getByPlaceholder(/https:\/\/tuyendung\.example/i);
    await urlInput.fill("https://tin-demo.example/dang-nhap");
    await page.getByRole("button", { name: /Lấy nội dung từ liên kết/i }).click();

    await expect(page.locator("form").getByRole("alert")).toContainText("Trang DEMO yêu cầu đăng nhập; không trích xuất nội dung.");

    // 2. Lỗi timeout
    await page.unroute("**/api/v1/extractions/url");
    await page.route("**/api/v1/extractions/url", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "req-e2e-timeout",
          success: false,
          source_type: "url",
          text: null,
          failure_vi: "Hết thời gian chờ phản hồi từ trang nguồn (timeout). Vui lòng thử lại hoặc dán văn bản trực tiếp.",
        }),
      });
    });

    await urlInput.fill("https://slow-recruitment.example/timeout");
    await page.getByRole("button", { name: /Lấy nội dung từ liên kết/i }).click();

    await expect(page.locator("form").getByRole("alert")).toContainText("Hết thời gian chờ phản hồi từ trang nguồn (timeout)");
  });
});
