import { expect, test } from "./fixtures";

test.describe("Xác thực và Quản lý dữ liệu cá nhân (R2)", () => {
  const uniqueEmail = `user_${Date.now()}@example.com`;
  const securePassword = "secure_password_15_chars";
  const initialName = "Kiểm Thử Viên R2";

  for (const mode of ["register", "login"] as const) {
    test(`phân tích khách -> điều hướng không reload -> ${mode} -> đồng ý nhận đúng kết quả`, async ({ page, request }) => {
      const email = `claim_${mode}_${Date.now()}@example.com`;
      if (mode === "login") {
        const response = await request.post("/api/v1/auth/register", {
          data: { email, password: securePassword, full_name: initialName },
        });
        expect(response.status()).toBe(201);
      }

      await page.goto("/analyze");
      await page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i).fill(
        "Công ty Kiểm thử R2 tuyển Lập trình viên tại Hà Nội. Lương 20 triệu/tháng. Liên hệ hr@r2.example. Không thu phí."
      );
      await page.getByRole("button", { name: /Phân tích tin tuyển dụng/i }).click();
      await expect(page).toHaveURL(/\/analyze\?id=/);
      const analysisId = new URL(page.url()).searchParams.get("id");
      expect(analysisId).toBeTruthy();

      // Keep AuthProvider mounted, just as when following links in the real guest journey.
      await page.getByRole("link", { name: "Trang chủ", exact: true }).click();
      await page.getByRole("banner").getByRole("link", { name: "Đăng nhập", exact: true }).click();
      if (mode === "register") await page.getByRole("link", { name: "Đăng ký ngay", exact: true }).click();
      if (mode === "register") await page.getByLabel("Họ và tên").fill(initialName);
      await page.getByLabel("Email").fill(email);
      await page.getByLabel("Mật khẩu", { exact: true }).fill(securePassword);
      await page.getByRole("button", { name: mode === "register" ? "Đăng ký tài khoản" : "Đăng nhập", exact: true }).click();

      await expect(page.getByRole("heading", { name: "Tìm thấy kết quả phân tích phiên khách" })).toBeVisible();
      await expect(page).toHaveURL(new RegExp(`/${mode}$`));
      await page.getByRole("button", { name: "Nhận vào tài khoản" }).click();
      await expect(page).toHaveURL(/\/dashboard/);
      await page.getByRole("banner").getByRole("link", { name: "Lịch sử", exact: true }).click();
      await expect(page.locator(`a[href="/analyze?id=${analysisId}"]`)).toBeVisible();
      await page.reload();
      await page.locator(`a[href="/analyze?id=${analysisId}"]`).click();
      await expect(page.getByText(/Kết quả được lưu trong tài khoản của bạn/)).toBeVisible();
    });
  }

  test("Đăng ký -> Đăng xuất -> Đăng nhập -> Hồ sơ -> Phân tích cá nhân & Đã lưu", async ({
    page,
  }) => {
    // 1. Kiểm tra đăng ký và ràng buộc mật khẩu >= 15 ký tự
    await page.goto("/register");
    await expect(page.getByRole("heading", { level: 1, name: "Tạo tài khoản JobShield" })).toBeVisible();

    await page.getByLabel(/Họ và tên/i).fill(initialName);
    await page.getByLabel(/Email/i).fill(uniqueEmail);
    await page.getByLabel(/Mật khẩu/i).fill("short_pwd");
    await page.getByRole("button", { name: "Đăng ký tài khoản" }).click();

    // Thông báo lỗi mật khẩu tối thiểu 15 ký tự
    await expect(page.getByText(/Mật khẩu phải có tối thiểu 15 ký tự/i)).toBeVisible();

    // Điền mật khẩu hợp lệ và đăng ký thành công
    await page.getByLabel(/Mật khẩu/i).fill(securePassword);
    await page.getByRole("button", { name: "Đăng ký tài khoản" }).click();

    // Chuyển hướng tới Dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: new RegExp(initialName, "i") })).toBeVisible();

    // 2. Cập nhật hồ sơ cá nhân
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Hồ sơ & Bảo mật" })).toBeVisible();
    const emailField = page.getByLabel(/Email/i);
    await expect(emailField).toBeDisabled();
    await expect(emailField).toHaveValue(uniqueEmail);

    const updatedName = "Kiểm Thử Viên Đã Đổi Tên";
    const nameField = page.getByLabel(/Họ và tên/i);
    await nameField.fill(updatedName);
    await page.getByRole("button", { name: "Lưu thay đổi" }).click();
    await expect(page.getByText(/Cập nhật họ và tên thành công/i)).toBeVisible();

    // 3. Đăng xuất và đăng nhập lại
    await page.getByRole("button", { name: "Đăng xuất" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/login");
    await page.getByLabel(/Email/i).fill(uniqueEmail);
    await page.getByLabel(/Mật khẩu/i).fill("wrong_password_test_15ch");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByText(/Email hoặc mật khẩu không chính xác/i)).toBeVisible();

    await page.getByLabel(/Mật khẩu/i).fill(securePassword);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: new RegExp(updatedName, "i") })).toBeVisible();

    // 4. Tạo bài phân tích khi đã đăng nhập
    await page.goto("/analyze");
    const textarea = page.getByPlaceholder(/Dán toàn bộ văn bản tin tuyển dụng/i);
    await textarea.fill(
      "Công ty Cổ phần Công nghệ ABC tuyển dụng Lập trình viên Fullstack React Python. Lương: 20-30 triệu/tháng. Liên hệ: tuyendung@abc.example. Không thu phí."
    );
    await page.getByRole("button", { name: /Phân tích tin tuyển dụng/i }).click();

    await expect(page.getByText(/Mức độ: Ít dấu hiệu rủi ro/i)).toBeVisible({ timeout: 15_000 });
    // Kết quả phân tích hiển thị footer xác nhận đã lưu vào tài khoản (không phải phiên khách 24h)
    await expect(page.getByText(/Kết quả được lưu trong tài khoản của bạn/i)).toBeVisible();

    await page.goto("/dashboard");
    await expect(page.getByText("1 (100%)").locator("..")).toContainText("Ít dấu hiệu rủi ro");

    // 5. Kiểm tra Lịch sử phân tích
    await page.goto("/history");
    await expect(page.getByText("Lập trình viên Fullstack React Python")).toBeVisible();

    // 6. Lưu bài phân tích và kiểm tra trang Đã lưu
    const saveBtn = page.getByRole("button", { name: "Lưu" }).first();
    await saveBtn.click();
    await expect(page.getByRole("button", { name: "Bỏ lưu" })).toBeVisible();

    await page.goto("/saved");
    await expect(page.getByText("Lập trình viên Fullstack React Python")).toBeVisible();

    // 7. Bỏ lưu bài
    await page.getByRole("button", { name: "Bỏ lưu" }).first().click();
    await expect(page.getByText(/Chưa có tin tuyển dụng nào được lưu/i)).toBeVisible();
  });

  test("lỗi kết nối cho phép thử lại; đổi mật khẩu kết thúc phiên và yêu cầu đăng nhập lại", async ({ page }) => {
    const email = `security_${Date.now()}@example.com`;
    const newPassword = "replacement_password_2026";
    await page.goto("/register");
    await page.getByLabel(/Họ và tên/i).fill("Kiểm thử phiên R2");
    await page.getByLabel(/Email/i).fill("email-khong-hop-le");
    await page.getByLabel(/Mật khẩu/i).fill(securePassword);
    await page.getByRole("button", { name: "Đăng ký tài khoản" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Email không hợp lệ" })).toBeVisible();
    await page.getByLabel(/Email/i).fill(email);
    await page.getByRole("button", { name: "Đăng ký tài khoản" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    let unavailable = true;
    await page.route("**/api/v1/users/me", async route => {
      if (route.request().method() === "GET" && unavailable) {
        unavailable = false;
        await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
      } else {
        await route.continue();
      }
    });
    await page.reload();
    await expect(page.getByRole("alert").filter({ hasText: "Không thể tải thông tin tài khoản" })).toBeVisible();
    expect(await page.evaluate(() => sessionStorage.getItem("jobshield_auth_token"))).toBeTruthy();
    await page.getByRole("button", { name: "Thử lại" }).click();
    await expect(page.getByRole("heading", { name: /Xin chào, Kiểm thử phiên R2/ })).toBeVisible();

    await page.goto("/profile");
    await page.getByLabel("Mật khẩu hiện tại").fill(securePassword);
    await page.getByLabel("Mật khẩu mới", { exact: true }).fill(newPassword);
    await page.getByLabel("Xác nhận mật khẩu mới").fill(newPassword);
    await page.getByRole("button", { name: "Đổi mật khẩu" }).click();
    await expect(page).toHaveURL(/\/login/);
    expect(await page.evaluate(() => sessionStorage.getItem("jobshield_auth_token"))).toBeNull();

    await page.getByLabel(/Email/i).fill(email);
    await page.getByLabel(/Mật khẩu/i).fill(securePassword);
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Email hoặc mật khẩu không chính xác" })).toBeVisible();
    await page.getByLabel(/Mật khẩu/i).fill(newPassword);
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
