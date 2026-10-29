import { expect, test } from "./fixtures";

test("trang shell có styles và nút nhận focus bằng bàn phím", async ({ page }) => {
  await page.goto("/");

  const heading = page.getByRole("heading", { level: 1, name: "JobShield" });
  const button = page.getByRole("button", { name: "Nút kiểm tra giao diện" });

  await expect(heading).toBeVisible();
  await expect(heading).toHaveCSS("font-size", "36px");
  await expect(button).toBeVisible();
  await expect(button).toHaveCSS("display", "inline-flex");

  await page.keyboard.press("Tab");
  await expect(button).toBeFocused();
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
