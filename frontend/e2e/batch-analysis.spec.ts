import { expect, test } from "./fixtures";
import type { AnalysisResponse, BatchAnalysisResponse } from "../src/types/api";

const mockAnalysisItem1: AnalysisResponse = {
  id: "analysis-item-1",
  risk_label_vi: "Rủi ro cao",
  risk_score: 85,
  verification_label_vi: "Chưa xác minh",
  finding_vi: "Phát hiện dấu hiệu nạp tiền đặt cọc và hoa hồng bất thường.",
  job: {
    company_name: "Công ty TNHH Quảng Cáo Lừa Đảo",
    job_title: "Cộng tác viên xử lý đơn hàng Shopee",
    salary: "20 - 30 triệu/tháng",
    location: "Làm việc tại nhà",
    employment_type: "Bán thời gian",
    contact_email: "tuyendung@lua-dao.example",
    contact_phone: null,
    recruitment_website: "https://tuyendung.example/job-lua-dao-1",
    application_requirements: "Có điện thoại kết nối mạng và tài khoản ngân hàng",
    required_payments: "Yêu cầu đặt cọc tiền đơn hàng trước khi nhận hoa hồng",
    suspicious_instructions: "Liên hệ làm nhiệm vụ qua nhóm Telegram",
  },
  indicators: [
    {
      category_vi: "Đặt cọc / Nạp tiền",
      rule_id: "RULE_DEPOSIT",
      matched_quote: "Yêu cầu đặt cọc tiền đơn hàng trước khi nhận hoa hồng",
    },
  ],
  evidence: {
    matched_sources: [],
    missing_vi: ["Không có giấy phép kinh doanh"],
    limitations_vi: [],
    is_demo: true,
  },
  actions_vi: [
    "Tuyệt đối không chuyển tiền đặt cọc dưới bất kỳ hình thức nào.",
    "Báo cáo tin tuyển dụng có dấu hiệu lừa đảo.",
  ],
  engine_version: "1.0",
  rules_version: "2026.11",
  created_at: "2026-11-03T10:00:00Z",
};

const mockAnalysisItem2: AnalysisResponse = {
  id: "analysis-item-2",
  risk_label_vi: "Ít dấu hiệu rủi ro",
  risk_score: 10,
  verification_label_vi: "Khớp nguồn đã xác minh",
  finding_vi: "Tin tuyển dụng có thông tin minh bạch, đã đối soát pháp nhân doanh nghiệp.",
  job: {
    company_name: "Công ty Cổ phần Công nghệ An Toàn",
    job_title: "Kỹ sư Kiểm thử Phần mềm QA",
    salary: "15 - 20 triệu/tháng",
    location: "Hà Nội",
    employment_type: "Toàn thời gian",
    contact_email: "hr@antoan.example",
    contact_phone: "02431234567",
    recruitment_website: "https://tuyendung.example/job-an-toan-2",
    application_requirements: "Tốt nghiệp đại học chuyên ngành CNTT",
    required_payments: null,
    suspicious_instructions: null,
  },
  indicators: [],
  evidence: {
    matched_sources: [
      {
        id: "source-gov-1",
        url: "https://dichvuthongtin.dkkd.gov.vn",
        label_vi: "Cổng thông tin quốc gia về đăng ký doanh nghiệp",
        verified_at: "2026-11-03T09:00:00Z",
      },
    ],
    missing_vi: [],
    limitations_vi: [],
    is_demo: false,
  },
  actions_vi: [
    "Tìm hiểu thêm quy trình phỏng vấn qua các kênh chính thức của công ty.",
  ],
  engine_version: "1.0",
  rules_version: "2026.11",
  created_at: "2026-11-03T10:00:00Z",
};

test.describe("Kiểm tra nhiều tin tuyển dụng (/analyze - Batch Analysis)", () => {
  test("chuyển chế độ Một tin -> Nhiều tin và kiểm tra xác thực form (validation)", async ({
    page,
  }) => {
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    await page.goto("/analyze");
    expect(pageErrors).toEqual([]);

    // 1. Kiểm tra mặc định ở chế độ Một tin
    const singleTab = page.getByRole("tab", { name: "Một tin" });
    const batchTab = page.getByRole("tab", { name: "Nhiều tin" });

    await expect(singleTab).toHaveAttribute("aria-selected", "true");
    await expect(batchTab).toHaveAttribute("aria-selected", "false");
    await expect(
      page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i)
    ).toBeVisible();

    // 2. Chuyển sang chế độ Nhiều tin
    await batchTab.click();
    await expect(batchTab).toHaveAttribute("aria-selected", "true");
    await expect(singleTab).toHaveAttribute("aria-selected", "false");

    // Phương thức nhập theo lô hiển thị
    await expect(page.getByText("Phương thức nhập theo lô")).toBeVisible();
    const urlsModeTab = page.getByRole("tab", { name: /Liên kết \(URLs\)/i });
    const contentModeTab = page.getByRole("tab", { name: /Nội dung \(Văn bản\)/i });
    await expect(urlsModeTab).toBeVisible();
    await expect(contentModeTab).toBeVisible();

    // 3. Kiểm tra validation chế độ Liên kết (URLs)
    const submitBtn = page.getByRole("button", { name: /Kiểm tra tất cả/i });
    await expect(submitBtn).toBeDisabled();

    const urlsTextarea = page.getByPlaceholder(/https:\/\/tuyendung\.example\/job-1/i);
    await expect(urlsTextarea).toBeVisible();

    // Nhập URL không hợp lệ
    await urlsTextarea.fill("khong-phai-duong-dan-hop-le");
    await expect(
      page.getByText(/không phải URL http\(s\) hợp lệ/i)
    ).toBeVisible();
    await expect(submitBtn).toBeDisabled();

    // Nhập 2 URL hợp lệ
    await urlsTextarea.fill(
      "https://tuyendung.example/job-1\nhttps://tuyendung.example/job-2"
    );
    await expect(page.getByText("Đã nhận diện: 2/10 liên kết")).toBeVisible();
    await expect(
      page.getByText(/không phải URL http\(s\) hợp lệ/i)
    ).not.toBeVisible();
    await expect(submitBtn).toBeEnabled();

    // 4. Kiểm tra validation chế độ Nội dung (Văn bản)
    await contentModeTab.click();
    await expect(contentModeTab).toHaveAttribute("aria-selected", "true");

    // Hai ô khởi tạo ban đầu để trống -> submit phải disabled
    await expect(page.getByText("Đã nhập: 0/10 tin")).toBeVisible();
    await expect(submitBtn).toBeDisabled();

    // Nhập nội dung vào ô Tin #1
    const firstBox = page.getByPlaceholder(/Dán nội dung tin tuyển dụng #1/i);
    await firstBox.fill(
      "Công ty Mẫu XYZ tuyển thực tập sinh lập trình frontend, không yêu cầu kinh nghiệm."
    );
    await expect(page.getByText("Đã nhập: 1/10 tin")).toBeVisible();
    await expect(submitBtn).toBeEnabled();

    // Thêm ô tin tuyển dụng
    const addBoxBtn = page.getByRole("button", { name: /Thêm tin tuyển dụng/i });
    await addBoxBtn.click();
    await expect(
      page.getByPlaceholder(/Dán nội dung tin tuyển dụng #3/i)
    ).toBeVisible();

    // Xóa ô tin tuyển dụng #3
    const removeBox3Btn = page.getByRole("button", { name: /Xóa tin #3/i });
    await removeBox3Btn.click();
    await expect(
      page.getByPlaceholder(/Dán nội dung tin tuyển dụng #3/i)
    ).not.toBeVisible();

    expect(pageErrors).toEqual([]);
  });

  test("trình duyệt -> API thật: guest mới, hỗn hợp text/URL, tải lại khi đang xử lý và xem chi tiết", async ({
    page,
    request,
  }) => {
    const fixture = await request.get("/api/v1/__e2e__/url-fixture");
    expect(fixture.status(), "CI/local must start the isolated E2E backend entry point").toBe(200);
    expect(await fixture.json()).toEqual({ ready: true, kind: "mock-transport" });
    await request.post("/api/v1/__e2e__/url-reset");
    try {

    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));
    await page.goto("/analyze");
    expect(await page.evaluate(() => sessionStorage.getItem("jobshield_guest_token"))).toBeNull();

    let postedItems: Array<{ type: string; value: string }> = [];
    let postStartedAt = 0;
    let postElapsedMs = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && new URL(req.url()).pathname === "/api/v1/batches/analyses") {
        postStartedAt = Date.now();
        postedItems = (req.postDataJSON() as { items?: Array<{ type: string; value: string }> }).items ?? [];
      }
    });
    page.on("response", (res) => {
      if (res.request().method() === "POST" && new URL(res.url()).pathname === "/api/v1/batches/analyses") {
        postElapsedMs = Date.now() - postStartedAt;
      }
    });

    await page.getByRole("tab", { name: "Nhiều tin" }).click();
    await page.getByRole("tab", { name: "Kết hợp" }).click();
    await page.getByPlaceholder("Dán nội dung tin tuyển dụng #1 vào đây...").fill(
      "Công ty E2E A tuyển nhân viên kiểm thử phần mềm. Lương 15 triệu đồng/tháng. Không yêu cầu đặt cọc."
    );
    const successUrl = "http://8.8.8.8/jobshield-e2e-success";
    const errorUrl = "http://8.8.8.8/jobshield-e2e-error";
    await page.locator("#batch-urls-input").fill(`${successUrl}\n${errorUrl}`);

    const createResponsePromise = page.waitForResponse(
      (res) => res.request().method() === "POST" && new URL(res.url()).pathname === "/api/v1/batches/analyses"
    );
    await page.getByRole("button", { name: /Kiểm tra tất cả/i }).click();
    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    expect(postedItems.map((item) => item.type)).toEqual(["url", "url", "text"]);
    expect(postedItems.map((item) => item.value)).toEqual([
      successUrl,
      errorUrl,
      "Công ty E2E A tuyển nhân viên kiểm thử phần mềm. Lương 15 triệu đồng/tháng. Không yêu cầu đặt cọc.",
    ]);

    const created = (await createResponse.json()) as BatchAnalysisResponse;
    expect(created.items).toHaveLength(3);
    expect(created.items.every((item) => item.status === "pending")).toBe(true);
    expect(postElapsedMs).toBeGreaterThan(0);
    console.info(`[batch-e2e] Three-item create POST: ${postElapsedMs}ms (observed separately from pass/fail gate)`);
    await expect(page).toHaveURL(new RegExp(`batch_id=${created.id}`));

    await expect.poll(async () => {
      const response = await request.get("/api/v1/__e2e__/url-state");
      return response.json();
    }, { timeout: 10_000 }).toEqual({ started: true, released: false });

    const reloadedSnapshotPromise = page.waitForResponse((res) => {
      return res.request().method() === "GET" &&
        new RegExp(`/api/v1/batches/analyses/${created.id}$`).test(new URL(res.url()).pathname);
    });
    await page.reload();
    const reloadedSnapshotResponse = await reloadedSnapshotPromise;
    expect(reloadedSnapshotResponse.status()).toBe(200);
    const reloadedSnapshot = (await reloadedSnapshotResponse.json()) as BatchAnalysisResponse;
    expect(reloadedSnapshot.status).toBe("processing");
    expect(reloadedSnapshot.items.some((item) => item.status === "processing")).toBe(true);
    await expect(page.getByText(/Đang xử lý/).first()).toBeVisible();

    const release = await request.post("/api/v1/__e2e__/url-release");
    expect(release.status()).toBe(200);

    await expect(page.getByText("Hoàn thành", { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Đã xử lý 3/3 tin")).toBeVisible();
    await expect(page.getByText("Trang nguồn trả về lỗi HTTP 503. Vui lòng dán văn bản trực tiếp.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Xem chi tiết" })).toHaveCount(2);

    await page.getByRole("button", { name: "Xem chi tiết" }).first().click();
    await expect(page.getByText("Kết luận sơ bộ")).toBeVisible();
    await expect(page.getByText("Công ty E2E A", { exact: false }).first()).toBeVisible();
    await page.getByRole("button", { name: /Quay lại danh sách/i }).first().click();
    await expect(page.getByText("Danh sách tin tuyển dụng (3)")).toBeVisible();
    expect(pageErrors).toEqual([]);
    } finally {
      await request.post("/api/v1/__e2e__/url-release").catch(() => undefined);
    }
  });

  test("API thật tạo và hoàn thành đủ 10 URL", async ({ page, request }) => {
    const fixture = await request.get("/api/v1/__e2e__/url-fixture");
    expect(fixture.status(), "The real batch smoke requires the isolated E2E backend entry point").toBe(200);
    await request.post("/api/v1/__e2e__/url-reset");
    await request.post("/api/v1/__e2e__/url-release");
    await page.goto("/analyze");
    expect(await page.evaluate(() => sessionStorage.getItem("jobshield_guest_token"))).toBeNull();
    await page.getByRole("tab", { name: "Nhiều tin" }).click();

    const urls = Array.from({ length: 10 }, (_, index) =>
      `http://8.8.8.8/jobshield-e2e-success?item=${index + 1}`
    );
    await page.locator("#batch-urls-input").fill(urls.join("\n"));
    const createResponsePromise = page.waitForResponse(
      (res) => res.request().method() === "POST" && new URL(res.url()).pathname === "/api/v1/batches/analyses"
    );
    const createStartedAt = Date.now();
    await page.getByRole("button", { name: /Kiểm tra tất cả/i }).click();
    const createResponse = await createResponsePromise;
    const createElapsedMs = Date.now() - createStartedAt;
    expect(createResponse.status()).toBe(201);
    const created = (await createResponse.json()) as BatchAnalysisResponse;
    expect(created.total_items).toBe(10);
    expect(created.items).toHaveLength(10);
    console.info(`[batch-e2e] Ten-item create POST: ${createElapsedMs}ms (observed separately from pass/fail gate)`);

    await expect(page.getByText("Hoàn thành", { exact: true })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Đã xử lý 10/10 tin")).toBeVisible();
    await expect(page.getByText("Danh sách tin tuyển dụng (10)")).toBeVisible();
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  test("gửi batch -> polling tiến độ -> hiển thị danh sách kết quả -> xem chi tiết in-place -> quay lại danh sách", async ({
    page,
  }) => {
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    const batchId = "batch-e2e-demo-12345";
    let pollCount = 0;

    // 1. Mock POST tạo batch mới
    await page.route("**/api/v1/batches/analyses", async (route) => {
      if (route.request().method() === "POST") {
        const postData = route.request().postDataJSON();
        expect(postData.items).toHaveLength(2);
        const res: BatchAnalysisResponse = {
          id: batchId,
          status: "processing",
          total_items: 2,
          processed_items: 0,
          created_at: "2026-11-03T10:00:00Z",
          items: [
            {
              id: "item-1",
              item_order: 1,
              input_type: "url",
              input_value: "https://tuyendung.example/job-lua-dao-1",
              status: "processing",
            },
            {
              id: "item-2",
              item_order: 2,
              input_type: "url",
              input_value: "https://tuyendung.example/job-an-toan-2",
              status: "pending",
            },
          ],
        };
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(res),
        });
      } else {
        await route.continue();
      }
    });

    // 2. Mock GET polling trạng thái batch
    await page.route(`**/api/v1/batches/analyses/${batchId}`, async (route) => {
      pollCount++;
      if (pollCount === 1) {
        // Đợt poll 1: đã xong item 1, item 2 đang xử lý
        const step1: BatchAnalysisResponse = {
          id: batchId,
          status: "processing",
          total_items: 2,
          processed_items: 1,
          created_at: "2026-11-03T10:00:00Z",
          items: [
            {
              id: "item-1",
              item_order: 1,
              input_type: "url",
              input_value: "https://tuyendung.example/job-lua-dao-1",
              status: "success",
              analysis_id: "analysis-item-1",
              analysis: mockAnalysisItem1,
            },
            {
              id: "item-2",
              item_order: 2,
              input_type: "url",
              input_value: "https://tuyendung.example/job-an-toan-2",
              status: "processing",
            },
          ],
        };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(step1),
        });
      } else {
        // Đợt poll 2 trở đi: hoàn thành cả 2 tin
        const step2: BatchAnalysisResponse = {
          id: batchId,
          status: "completed",
          total_items: 2,
          processed_items: 2,
          created_at: "2026-11-03T10:00:00Z",
          items: [
            {
              id: "item-1",
              item_order: 1,
              input_type: "url",
              input_value: "https://tuyendung.example/job-lua-dao-1",
              status: "success",
              analysis_id: "analysis-item-1",
              analysis: mockAnalysisItem1,
            },
            {
              id: "item-2",
              item_order: 2,
              input_type: "url",
              input_value: "https://tuyendung.example/job-an-toan-2",
              status: "success",
              analysis_id: "analysis-item-2",
              analysis: mockAnalysisItem2,
            },
          ],
        };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(step2),
        });
      }
    });

    await page.goto("/analyze");
    await page.getByRole("tab", { name: "Nhiều tin" }).click();

    const urlsTextarea = page.getByPlaceholder(/https:\/\/tuyendung\.example\/job-1/i);
    await urlsTextarea.fill(
      "https://tuyendung.example/job-lua-dao-1\nhttps://tuyendung.example/job-an-toan-2"
    );

    const submitBtn = page.getByRole("button", { name: /Kiểm tra tất cả/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 3. Xác nhận URL cập nhật tham số ?batch_id=...
    await expect(page).toHaveURL(new RegExp(`batch_id=${batchId}`));

    // 4. Kiểm tra thanh tiến độ và huy hiệu hoàn thành
    const progressBar = page.getByRole("progressbar");
    await expect(progressBar).toBeVisible();

    // Chờ quá trình polling cập nhật thành công cả 2 tin
    await expect(page.getByText("Hoàn thành")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Đã xử lý 2/2 tin")).toBeVisible();
    await expect(page.getByText("100%", { exact: true })).toBeVisible();

    // 5. Kiểm tra thông tin các tin trong danh sách kết quả
    // Tin #1: Cộng tác viên Shopee - Rủi ro cao
    await expect(
      page.getByText("Cộng tác viên xử lý đơn hàng Shopee")
    ).toBeVisible();
    await expect(
      page.getByText("Công ty TNHH Quảng Cáo Lừa Đảo")
    ).toBeVisible();
    await expect(
      page.locator("span", { hasText: /^Rủi ro cao$/ }).first()
    ).toBeVisible();

    // Tin #2: Kỹ sư QA - Ít dấu hiệu rủi ro
    await expect(
      page.getByText("Kỹ sư Kiểm thử Phần mềm QA")
    ).toBeVisible();
    await expect(
      page.getByText("Công ty Cổ phần Công nghệ An Toàn")
    ).toBeVisible();
    await expect(
      page.locator("span", { hasText: /^Ít dấu hiệu rủi ro$/ }).first()
    ).toBeVisible();

    // 6. Kiểm tra xem chi tiết in-place
    const detailButtons = page.getByRole("button", { name: /Xem chi tiết/i });
    await expect(detailButtons.first()).toBeVisible();
    await detailButtons.first().click();

    // Khung AnalysisResults được hiển thị với nhãn nút quay lại
    await expect(
      page.getByText("Phát hiện dấu hiệu nạp tiền đặt cọc và hoa hồng bất thường.")
    ).toBeVisible();
    const backBtn = page
      .getByRole("button", { name: /Quay lại danh sách/i })
      .first();
    await expect(backBtn).toBeVisible();

    // 7. Click quay lại danh sách
    await backBtn.click();
    await expect(
      page.getByText("Danh sách tin tuyển dụng (2)")
    ).toBeVisible();
    await expect(
      page.getByText("Cộng tác viên xử lý đơn hàng Shopee")
    ).toBeVisible();
    await expect(
      page.getByText("Kỹ sư Kiểm thử Phần mềm QA")
    ).toBeVisible();

    // 8. Tải lại trang (F5): giữ nguyên dữ liệu từ URL ?batch_id=...
    await page.reload();
    expect(pageErrors).toEqual([]);
    await expect(page).toHaveURL(new RegExp(`batch_id=${batchId}`));
    await expect(page.getByText("Hoàn thành")).toBeVisible();
    await expect(
      page.getByText("Cộng tác viên xử lý đơn hàng Shopee")
    ).toBeVisible();
  });

  test("hủy lượt thật: hàng đang chạy hoàn tất, hàng chờ được hủy", async ({
    page,
    request,
  }) => {
    const fixture = await request.get("/api/v1/__e2e__/url-fixture");
    expect(fixture.status()).toBe(200);
    await request.post("/api/v1/__e2e__/url-reset");
    try {
      const pageErrors: Error[] = [];
      page.on("pageerror", (err) => pageErrors.push(err));
      await page.goto("/analyze");
      expect(await page.evaluate(() => sessionStorage.getItem("jobshield_guest_token"))).toBeNull();
      await page.getByRole("tab", { name: "Nhiều tin" }).click();

      await page.locator("#batch-urls-input").fill(
        "http://8.8.8.8/jobshield-e2e-success?cancel=1\nhttp://8.8.8.8/jobshield-e2e-success?cancel=2"
      );
      const createResponsePromise = page.waitForResponse(
        (res) => res.request().method() === "POST" && new URL(res.url()).pathname === "/api/v1/batches/analyses"
      );
      await page.getByRole("button", { name: /Kiểm tra tất cả/i }).click();
      const createResponse = await createResponsePromise;
      expect(createResponse.status()).toBe(201);
      const created = (await createResponse.json()) as BatchAnalysisResponse;

      await expect.poll(async () => {
        const response = await request.get("/api/v1/__e2e__/url-state");
        return response.json();
      }, { timeout: 10_000 }).toEqual({ started: true, released: false });

      const cancelBtn = page.getByRole("button", { name: /Hủy lượt/i });
      await expect(cancelBtn).toBeVisible({ timeout: 10_000 });
      const cancelResponsePromise = page.waitForResponse(
        (res) => res.request().method() === "POST" &&
          new URL(res.url()).pathname === `/api/v1/batches/analyses/${created.id}/cancel`
      );
      await cancelBtn.click();
      const cancelResponse = await cancelResponsePromise;
      expect(cancelResponse.status()).toBe(200);
      const cancelled = (await cancelResponse.json()) as BatchAnalysisResponse;
      expect(cancelled.status).toBe("cancelled");
      expect(cancelled.processed_items).toBe(0);
      expect(cancelled.items.map((item) => item.status)).toEqual(["processing", "cancelled"]);

      await expect(page.getByText("Đã hủy").first()).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText("Đang xử lý...")).toBeVisible();
      await expect(page.getByText("Đang hủy / Đã hủy")).toBeVisible();
      await expect(cancelBtn).not.toBeVisible();

      const guestToken = await page.evaluate(() => sessionStorage.getItem("jobshield_guest_token"));
      expect(guestToken).toBeTruthy();
      const release = await request.post("/api/v1/__e2e__/url-release");
      expect(release.status()).toBe(200);
      await expect.poll(async () => {
        const response = await request.get(`/api/v1/batches/analyses/${created.id}`, {
          headers: { "x-guest-session-token": guestToken! },
        });
        const current = (await response.json()) as BatchAnalysisResponse;
        return {
          status: current.status,
          processed: current.processed_items,
          items: current.items.map((item) => item.status),
        };
      }, { timeout: 15_000 }).toEqual({
        status: "cancelled",
        processed: 1,
        items: ["success", "cancelled"],
      });
      await expect(page.getByRole("button", { name: /Kiểm tra lượt mới/i })).toBeVisible({ timeout: 10_000 });
      await expect(page.getByRole("button", { name: /Xem chi tiết/i })).toHaveCount(1);

      expect(pageErrors).toEqual([]);
    } finally {
      await request.post("/api/v1/__e2e__/url-release").catch(() => undefined);
    }
  });
});
