import { expect, test } from "./fixtures";

test("trang chủ có styles, font sans và điều hướng bằng bàn phím", async ({ page }) => {
  await page.goto("/");

  const heading = page.getByRole("heading", { level: 1, name: /lừa đảo việc làm/i });
  const button = page.getByRole("button", { name: "Nút kiểm tra giao diện" });

  await expect(heading).toBeVisible();
  await expect(heading).toHaveCSS("font-family", /sans-serif/);
  expect(await heading.evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(36);
  await expect(button).toBeVisible();
  await expect(button).toHaveCSS("display", /^(inline-)?flex$/);

  await page.keyboard.press("Tab");
  await expect(page.getByRole("banner").getByRole("link", { name: /JobShield/ })).toBeFocused();
});

test("mẫu từ trang chủ giữ nội dung khi điều hướng và tải lại", async ({ page }) => {
  const pageErrors: Error[] = [];
  page.on("pageerror", error => pageErrors.push(error));
  await page.goto("/");
  await page.getByRole("link", { name: "Phân tích mẫu này", exact: true }).first().click();
  await expect(page).toHaveURL(/\/analyze\?sample=/);
  const sample = new URL(page.url()).searchParams.get("sample")!;
  const textarea = page.getByLabel("Nội dung tin tuyển dụng cần phân tích");
  await expect(textarea).toHaveValue(sample);
  await page.reload();
  await expect(textarea).toHaveValue(sample);
  expect(pageErrors).toEqual([]);
});

test("route chưa triển khai trả 404 tiếng Việt thay vì lỗi server", async ({ page }) => {
  const routes = [
    "/analysis/g1-example",
    "/g1-missing-page",
  ];

  for (const route of routes) {
    await test.step(route, async () => {
      const response = await page.goto(route);

      expect(response?.status()).toBe(404);
      await expect(
        page.getByRole("heading", { name: "Không tìm thấy trang" }),
      ).toBeVisible();
      await expect(
        page.getByRole("link", { name: "Về trang chủ" }),
      ).toHaveAttribute("href", "/");
    });
  }
});
