import { expect, test } from "@playwright/test";

test.describe("Quản trị và Kiểm duyệt (R4.2 - R4.4)", () => {
  const normalUserEmail = `normal_${Date.now()}@example.com`;
  const securePassword = "secure_password_15_chars";

  test("Người dùng thông thường bị chặn truy cập /admin", async ({ page, request }) => {
    // 1. Đăng ký tài khoản thường
    const regRes = await request.post("/api/v1/auth/register", {
      data: {
        email: normalUserEmail,
        password: securePassword,
        full_name: "Người Dùng Thường",
      },
    });
    expect(regRes.status()).toBe(201);

    // 2. Đăng nhập
    await page.goto("/login");
    await page.getByLabel("Email").fill(normalUserEmail);
    await page.getByLabel("Mật khẩu").fill(securePassword);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    // 3. Cố gắng vào /admin
    await page.goto("/admin");
    await expect(page.getByText("Không có quyền truy cập")).toBeVisible();
    await expect(
      page.getByText("Khu vực này yêu cầu tài khoản có vai trò Quản trị viên (Admin).")
    ).toBeVisible();
  });

  test("Trang thông tin an toàn công khai /safety hiển thị nguyên tắc an toàn", async ({
    page,
  }) => {
    await page.goto("/safety");
    await expect(
      page.getByRole("heading", { name: /Thông tin An toàn & Cảnh báo Tuyển dụng/i })
    ).toBeVisible();
    await expect(
      page.getByText("3 Nguyên tắc an toàn cốt lõi khi tìm việc")
    ).toBeVisible();
    await expect(page.getByText("Tuyệt đối không đóng phí:")).toBeVisible();
  });
});

test("admin adds provenance and publishes, corrects and withdraws a warning", async ({ page, request }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin-r4-e2e@example.com");
  await page.getByLabel("Mật khẩu").fill("synthetic_admin_password_2026");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  const employer = `DEMO R4 Employer ${Date.now()}`;
  await page.goto("/admin/employers");
  await page.getByRole("button", { name: "+ Thêm nhà tuyển dụng" }).click();
  await page.getByLabel(/Tên pháp lý doanh nghiệp/).fill(employer);
  await page.getByRole("button", { name: "Thêm mới", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: employer });
  await row.getByRole("button", { name: "Nguồn & đối chiếu" }).click();
  const curation = page.getByRole("region", { name: `Nguồn & đối chiếu: ${employer}` });
  await curation.getByLabel("Tên nguồn", { exact: true }).fill("Reviewed source R4");
  await curation.getByLabel("URL nguồn công khai").fill("https://example.com/r4-evidence");
  await curation.getByLabel("Trích đoạn bằng chứng đã lược dữ liệu riêng").fill("Email hr-r4@example.com is the reviewed contact.");
  await curation.getByRole("button", { name: "Thêm nguồn", exact: true }).click();
  await expect(curation.getByRole("status")).toHaveText("Đã thêm nguồn xác minh.");
  await curation.getByLabel("Nguồn chứng minh").selectOption({ label: "Reviewed source R4" });
  await curation.getByLabel("Giá trị đã kiểm chứng").fill("hr-r4@example.com");
  await curation.getByRole("button", { name: "Thêm dữ kiện", exact: true }).click();
  await expect(curation.getByRole("status")).toHaveText("Đã thêm dữ kiện đối chiếu vào nguồn đã chọn.");
  const verification = await request.post("/api/v1/verifications", { data: { contact_email: "hr-r4@example.com" } });
  expect(verification.status()).toBe(200);
  expect((await verification.json()).matched_sources[0].url).toBe("https://example.com/r4-evidence");

  await page.goto("/admin/warnings");
  await page.getByRole("button", { name: "Tạo cảnh báo" }).click();
  await page.getByLabel("Tiêu đề công khai").fill("DEMO R4 warning published");
  await page.getByLabel("Tóm tắt công khai, đã lược thông tin người gửi").fill("Reviewed public evidence describes suspicious recruitment fees.");
  await page.getByLabel("Tên nguồn", { exact: true }).fill("Reviewed public evidence");
  await page.getByLabel("URL nguồn", { exact: true }).fill("https://example.com/warning-evidence");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Xuất bản cảnh báo", exact: true }).click();
  let warning = page.getByRole("listitem").filter({ hasText: "DEMO R4 warning published" });
  const originalHref = await warning.getByRole("link", { name: "Xem bản công khai" }).getAttribute("href");
  await warning.getByRole("button", { name: "Đính chính", exact: true }).click();
  await page.getByLabel("Tiêu đề công khai").fill("DEMO R4 corrected warning");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Xuất bản bản đính chính" }).click();
  warning = page.getByRole("listitem").filter({ hasText: "DEMO R4 corrected warning" });
  await expect(warning).toContainText("v2");
  const correctedHref = await warning.getByRole("link", { name: "Xem bản công khai" }).getAttribute("href");
  await warning.getByRole("button", { name: "Thu hồi", exact: true }).click();
  await page.getByLabel("Lý do thu hồi công khai").fill("Evidence corrected; withdraw this synthetic warning.");
  await page.getByRole("button", { name: "Xác nhận thu hồi" }).click();
  await expect(warning).toContainText("Đã thu hồi");
  await page.goto(originalHref!);
  await page.getByRole("link", { name: "Xem bản đính chính tiếp theo →" }).click();
  await expect(page).toHaveURL(correctedHref!);
  await expect(page.getByRole("status")).toContainText("Evidence corrected; withdraw this synthetic warning.");
});
