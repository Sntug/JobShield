import { expect, test } from "@playwright/test";

test.describe("Báo cáo tuyển dụng đáng ngờ (R4.1)", () => {
  const uniqueEmail = `reporter_${Date.now()}@example.com`;
  const securePassword = "secure_password_15_chars";
  const fullName = "Người Báo Cáo E2E";

  test("Đăng ký -> Gửi báo cáo kèm bằng chứng -> Xem danh sách báo cáo của tôi", async ({
    page,
    request,
  }) => {
    // 1. Đăng ký tài khoản
    const registerRes = await request.post("/api/v1/auth/register", {
      data: {
        email: uniqueEmail,
        password: securePassword,
        full_name: fullName,
      },
    });
    expect(registerRes.status()).toBe(201);

    // 2. Đăng nhập
    await page.goto("/login");
    await page.getByLabel("Email").fill(uniqueEmail);
    await page.getByLabel("Mật khẩu").fill(securePassword);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    // 3. Vào trang gửi báo cáo
    await page.goto("/reports/new");
    await expect(
      page.getByRole("heading", { name: /Gửi báo cáo tuyển dụng đáng ngờ/i })
    ).toBeVisible();

    // 4. Nhập mô tả và đính kèm bằng chứng
    await page.getByLabel(/Mô tả chi tiết sự việc/i).fill(
      "Đối tượng liên hệ qua Telegram yêu cầu nạp tiền 500k để nhận tài liệu tuyển dụng."
    );

    await page.getByLabel("Nội dung bằng chứng").fill("Ảnh chụp giao dịch chuyển khoản");
    await page.getByRole("button", { name: "Thêm" }).click();
    await expect(page.getByText("Ảnh chụp giao dịch chuyển khoản")).toBeVisible();

    // 5. Submit form
    await page.getByRole("button", { name: "Gửi báo cáo" }).click();
    await expect(page.getByText("Gửi báo cáo thành công!")).toBeVisible();

    // 6. Điều hướng tới danh sách báo cáo
    await page.getByRole("button", { name: "Xem danh sách báo cáo của tôi" }).click();
    await expect(page).toHaveURL(/\/reports/);

    // Xác nhận báo cáo vừa gửi xuất hiện trong danh sách với nhãn Chờ duyệt
    await expect(page.getByText("Phí tuyển dụng trước")).toBeVisible();
    await expect(page.getByText("Chờ duyệt")).toBeVisible();
  });
});
