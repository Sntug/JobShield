import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AuthForm } from "@/components/auth/auth-form";
import { RiskStatistics } from "@/components/dashboard/risk-statistics";
import { ProfileForm } from "@/components/profile/profile-form";

describe("AuthForm Component", () => {
  it("renders login form with accessible labels and submits valid credentials", async () => {
    const handleLogin = vi.fn().mockResolvedValue(undefined);
    render(<AuthForm mode="login" onSubmit={handleLogin} />);

    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mật khẩu/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Đăng nhập/i })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/i), {
      target: { value: "secure_password_15_chars" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Đăng nhập/i }));

    await waitFor(() => {
      expect(handleLogin).toHaveBeenCalledWith({
        email: "user@example.com",
        password: "secure_password_15_chars",
      });
    });
  });

  it("validates register form requires full name and password >= 15 chars", async () => {
    const handleRegister = vi.fn().mockResolvedValue(undefined);
    render(<AuthForm mode="register" onSubmit={handleRegister} />);

    expect(screen.getByLabelText(/Họ và tên/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mật khẩu/i)).toBeInTheDocument();

    // Nhập mật khẩu dưới 15 ký tự
    fireEvent.change(screen.getByLabelText(/Họ và tên/i), {
      target: { value: "Nguyễn Văn A" },
    });
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/i), {
      target: { value: "short_pwd" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Đăng ký/i }));

    expect(
      await screen.findByText(/Mật khẩu phải có tối thiểu 15 ký tự/i)
    ).toBeInTheDocument();
    expect(handleRegister).not.toHaveBeenCalled();

    // Nhập mật khẩu đủ 15 ký tự
    fireEvent.change(screen.getByLabelText(/Mật khẩu/i), {
      target: { value: "secure_password_15_chars" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Đăng ký/i }));

    await waitFor(() => {
      expect(handleRegister).toHaveBeenCalledWith({
        full_name: "Nguyễn Văn A",
        email: "test@example.com",
        password: "secure_password_15_chars",
      });
    });
  });
});

describe("RiskStatistics Component", () => {
  it("renders personal analysis counts and risk distribution", () => {
    const stats = {
      total_analyses: 12,
      saved_analyses: 4,
      risk_distribution: {
        "Rủi ro cao": 3,
        "Không đủ thông tin": 7,
        "Ít dấu hiệu rủi ro": 2,
      },
    };
    render(<RiskStatistics stats={stats} />);

    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText(/Tổng tin đã phân tích/i)).toBeInTheDocument();
    expect(screen.getByText(/Tin đã lưu/i)).toBeInTheDocument();
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
  });
});

describe("ProfileForm Component", () => {
  it("allows updating full name and changing password", async () => {
    const handleUpdateName = vi.fn().mockResolvedValue(undefined);
    const handleChangePassword = vi.fn().mockResolvedValue(undefined);

    const user = {
      id: "u1",
      email: "readonly@example.com",
      full_name: "Tên Cũ",
      role: "user",
      created_at: "2026-10-27T10:00:00Z",
    };

    render(
      <ProfileForm
        user={user}
        onUpdateName={handleUpdateName}
        onChangePassword={handleChangePassword}
      />
    );

    // Email ở chế độ chỉ đọc
    const emailInput = screen.getByLabelText(/Email/i);
    expect(emailInput).toHaveValue("readonly@example.com");
    expect(emailInput).toBeDisabled();

    // Đổi tên
    const nameInput = screen.getByLabelText(/Họ và tên/i);
    fireEvent.change(nameInput, { target: { value: "Tên Mới" } });
    fireEvent.click(screen.getByRole("button", { name: /Lưu thay đổi/i }));

    await waitFor(() => {
      expect(handleUpdateName).toHaveBeenCalledWith("Tên Mới");
    });

    // Đổi mật khẩu
    fireEvent.change(screen.getByLabelText(/Mật khẩu hiện tại/i), {
      target: { value: "old_secure_password_15ch" },
    });
    fireEvent.change(screen.getByLabelText(/^Mật khẩu mới$/i), {
      target: { value: "new_secure_password_15ch" },
    });
    fireEvent.change(screen.getByLabelText(/Xác nhận mật khẩu mới/i), {
      target: { value: "new_secure_password_15ch" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Đổi mật khẩu/i }));

    await waitFor(() => {
      expect(handleChangePassword).toHaveBeenCalledWith(
        "old_secure_password_15ch",
        "new_secure_password_15ch"
      );
    });
  });
});
