import { expect, test } from "@playwright/test";

test("xác minh giữ cookie truy cập của Preview cùng origin", async ({ page, context, baseURL }) => {
  await context.addCookies([{ name: "preview_access_test", value: "allowed", url: baseURL! }]);
  await page.route("**/api/v1/verifications", async route => {
    const headers = await route.request().allHeaders();
    if (!headers.cookie?.includes("preview_access_test=allowed")) {
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: "Preview authentication required" }) });
      return;
    }
    await route.continue();
  });
  await page.goto("/verify-employer");
  await page.getByLabel("Mã số thuế").fill("0000000401");
  await page.getByRole("button", { name: "Đối chiếu thông tin", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Khớp nguồn đã xác minh", exact: true })).toBeVisible();
});

test("đối chiếu thật, provenance, reset và dữ liệu ngân hàng không lưu", async ({ page }) => {
  await page.goto("/verify-employer");
  await page.getByLabel("Mã số thuế").fill("0000000401");
  await page.route("**/api/v1/verifications", async route => {
    await new Promise(resolve => setTimeout(resolve, 250));
    await route.continue();
  });
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("button", { name: /Đang đối chiếu/ })).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Khớp nguồn đã xác minh", exact: true })).toBeFocused();
  await expect(page.getByText(/Phiên bản nguồn: 1/)).toBeVisible();
  await expect(page.getByRole("link", { name: /Mở nguồn:/ })).toHaveAttribute("href", "https://company-1.example/about");
  await expect(page.getByText(/Khớp nguồn không xác nhận tin tuyển dụng thật, an toàn hoặc nên chuyển tiền/)).toBeVisible();
  await page.getByRole("button", { name: "Kiểm tra thông tin khác" }).click();
  await expect(page.getByLabel("Mã số thuế")).toHaveValue("");
  await page.getByText("Tài khoản ngân hàng (tùy chọn)", { exact: true }).click();
  await page.getByLabel("Ngân hàng", { exact: true }).fill("Bank E2E");
  await page.getByLabel("Số tài khoản").fill("000010001");
  await page.getByLabel("Chủ tài khoản").fill("CHU THE E2E");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Khớp nguồn đã xác minh", exact: true })).toBeVisible();
  await expect(page.getByText("000010001", { exact: false })).toHaveCount(0);
  await expect(page.getByText("CHU THE E2E", { exact: false })).toHaveCount(0);
  const storage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, url: location.href }));
  expect(storage).not.toContain("000010001");
  expect(storage).not.toContain("CHU THE E2E");
});

test("khớp một phần, trùng tên và hai định danh xung đột không thành nhãn khớp", async ({ page }) => {
  await page.goto("/verify-employer");
  await page.getByLabel("Mã số thuế").fill("0000000401");
  await page.getByLabel("Website tuyển dụng").fill("https://unlisted.example/jobs");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Chưa xác minh", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Kiểm tra thông tin khác" }).click();
  await page.getByLabel("Email liên hệ").fill("shared@e2e.example");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Không đủ dữ liệu", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Kiểm tra thông tin khác" }).click();
  await page.getByLabel("Mã số thuế").fill("0000000401");
  await page.getByLabel("Website tuyển dụng").fill("https://company-2.example/jobs");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Thông tin xung đột", exact: true })).toBeVisible();
});

test("lỗi dịch vụ giữ input, hỗ trợ thử lại và không giả thành chưa xác minh", async ({ page }) => {
  await page.goto("/verify-employer");
  await page.getByLabel("Tên công ty").fill("Công ty E2E A");
  await page.route("**/api/v1/verifications", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: { code: "SOURCE_STORE_UNAVAILABLE", message_vi: "Kho nguồn tạm thời không khả dụng." } }) }));
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Kho nguồn tạm thời không khả dụng." })).toHaveText("Kho nguồn tạm thời không khả dụng.");
  await expect(page.getByRole("alert").filter({ hasText: "Kho nguồn tạm thời không khả dụng." })).toBeFocused();
  await expect(page.getByLabel("Tên công ty")).toHaveValue("Công ty E2E A");
  await page.unroute("**/api/v1/verifications");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Không đủ dữ liệu", exact: true })).toBeVisible();
});

test("mobile 375px: nhập kênh độc lập, kết quả đọc được trong dark mode", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/verify-employer");
  await page.getByLabel("Link Telegram, Zalo hoặc Facebook").fill("https://t.me/e2e_only_profile_12345");
  await page.getByRole("button", { name: "Đối chiếu thông tin" }).click();
  await expect(page.getByRole("heading", { name: "Khớp nguồn đã xác minh", exact: true })).toBeVisible();
  await page.evaluate(() => document.documentElement.classList.add("dark"));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("verification-mobile-dark.png"), fullPage: true });
});
