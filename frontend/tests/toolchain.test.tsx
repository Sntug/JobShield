import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import HomePage from "@/app/(public)/page";

test("trang chủ hiển thị chức năng phân tích và nút kiểm tra", () => {
  render(<HomePage />);

  expect(
    screen.getByRole("heading", { level: 1, name: /lừa đảo việc làm/i }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Nút kiểm tra giao diện" }),
  ).toBeEnabled();
});
