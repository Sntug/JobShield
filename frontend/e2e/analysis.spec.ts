import { expect, test } from "./fixtures";

test.describe("Trang phân tích tin tuyển dụng (/analyze)", () => {
  test("luồng submit -> loading -> hiển thị kết quả -> reload -> Back/Forward -> phiên khác", async ({
    page,
    browser,
  }) => {
    // 1. Giám sát không có lỗi client runtime / hydration pageerror
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    await page.goto("/analyze");
    expect(pageErrors).toEqual([]);

    // Kiểm tra giao diện form khởi tạo
    const heading = page.getByRole("heading", { level: 1, name: "Phân tích tin tuyển dụng" });
    await expect(heading).toBeVisible();

    const textarea = page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i);
    await expect(textarea).toBeVisible();

    // Bộ đếm ký tự định dạng vi-VN chuẩn không lỗi hydration
    await expect(page.getByText("0 / 10.000 ký tự")).toBeVisible();

    const submitBtn = page.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    await expect(submitBtn).toBeDisabled();

    // 2. Nhập nội dung tin tuyển dụng
    const sampleText =
      "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. " +
      "Email: tuyendung@mau-a.example. Website: https://mau-a.example/tuyen-dung. Không thu phí hoặc đặt cọc.";

    await textarea.fill(sampleText);
    await expect(submitBtn).toBeEnabled();

    // 3. Click submit và kiểm tra trạng thái khóa/loading thực tế
    // Trì hoãn nhẹ request POST ban đầu để kiểm tra trạng thái loading ổn định, tránh flaky do phản hồi quá nhanh
    let delayed = false;
    await page.route("**/api/v1/analyses", async (route) => {
      if (!delayed && route.request().method() === "POST") {
        delayed = true;
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
      await route.continue();
    });

    await submitBtn.click();
    // Nút hiển thị đúng nhãn "Đang phân tích..." và ở trạng thái disabled
    await expect(page.getByRole("button", { name: /Đang phân tích/i })).toBeDisabled();

    // 4. Kết quả phân tích hiển thị và URL cập nhật ?id=...
    await expect(page.getByText(/Mức độ: Ít dấu hiệu rủi ro/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Công ty Mẫu A (DEMO)")).toBeVisible();
    await expect(page.getByText("Thực tập sinh kiểm thử")).toBeVisible();

    const url = new URL(page.url());
    const analysisId = url.searchParams.get("id");
    expect(analysisId).toBeTruthy();

    // 5. Tải lại trang (Reload): kết quả vẫn hiển thị nhờ sessionStorage token và URL ?id=...
    await page.reload();
    expect(pageErrors).toEqual([]);
    await expect(page.getByText("Công ty Mẫu A (DEMO)")).toBeVisible();
    await expect(page.getByText("Thực tập sinh kiểm thử")).toBeVisible();

    // 6. Trình duyệt Back: quay lại form nhập liệu, URL không còn ?id=...
    await page.goBack();
    await expect(page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i)).toBeVisible();
    const backUrl = new URL(page.url());
    expect(backUrl.searchParams.get("id")).toBeNull();

    // 7. Trình duyệt Forward: quay lại kết quả phân tích
    await page.goForward();
    await expect(page.getByText("Công ty Mẫu A (DEMO)")).toBeVisible();
    const fwdUrl = new URL(page.url());
    expect(fwdUrl.searchParams.get("id")).toBe(analysisId);

    // 8. Phiên khác (context mới không có sessionStorage token) truy cập vào ?id=...
    const guestBContext = await browser.newContext();
    const guestBPage = await guestBContext.newPage();
    const guestBErrors: Error[] = [];
    guestBPage.on("pageerror", (err) => guestBErrors.push(err));

    await guestBPage.goto(`/analyze?id=${analysisId}`);
    expect(guestBErrors).toEqual([]);

    // Hiển thị thông báo không có quyền/không có phiên và không hiển thị tin của Guest A
    await expect(
      guestBPage.getByText(/Không có phiên khách để đọc kết quả phân tích/i)
    ).toBeVisible();
    await expect(guestBPage.getByText("Thực tập sinh kiểm thử")).not.toBeVisible();

    await guestBContext.close();
  });
});
