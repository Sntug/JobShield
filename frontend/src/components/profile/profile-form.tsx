"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { User } from "@/types/api";

interface ProfileFormProps {
  user: User;
  onUpdateName: (name: string) => Promise<void>;
  onChangePassword: (oldPassword: string, newPassword: string) => Promise<void>;
}

export function ProfileForm({
  user,
  onUpdateName,
  onChangePassword,
}: ProfileFormProps) {
  const [fullName, setFullName] = useState(user.full_name);
  const [nameSuccess, setNameSuccess] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState(false);
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [pwdLoading, setPwdLoading] = useState(false);

  const handleNameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNameError(null);
    setNameSuccess(false);

    const trimmed = fullName.trim();
    if (!trimmed) {
      setNameError("Họ và tên không được để trống.");
      return;
    }

    setNameLoading(true);
    try {
      await onUpdateName(trimmed);
      setNameSuccess(true);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setNameError(error.message || "Cập nhật tên thất bại.");
    } finally {
      setNameLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError(null);
    setPwdSuccess(false);

    if (!oldPassword) {
      setPwdError("Vui lòng nhập mật khẩu hiện tại.");
      return;
    }

    if (newPassword.length < 15) {
      setPwdError("Mật khẩu mới phải có tối thiểu 15 ký tự.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPwdError("Xác nhận mật khẩu mới không khớp.");
      return;
    }

    setPwdLoading(true);
    try {
      await onChangePassword(oldPassword, newPassword);
      setPwdSuccess(true);
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const error = err as { message?: string };
      setPwdError(error.message || "Đổi mật khẩu thất bại.");
    } finally {
      setPwdLoading(false);
    }
  };

  return (
    <div className="space-y-10 max-w-xl">
      {/* Cập nhật thông tin cơ bản */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Thông tin tài khoản
        </h2>
        <form onSubmit={handleNameSubmit} className="space-y-4">
          {nameSuccess && (
            <div className="rounded-md bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-800">
              Cập nhật họ và tên thành công!
            </div>
          )}
          {nameError && (
            <div role="alert" className="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-800">
              {nameError}
            </div>
          )}

          <div>
            <label htmlFor="profile_email" className="block text-sm font-medium text-slate-700 mb-1">
              Email (không thể thay đổi)
            </label>
            <input
              id="profile_email"
              type="email"
              disabled
              value={user.email}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-500 cursor-not-allowed"
            />
          </div>

          <div>
            <label htmlFor="profile_fullname" className="block text-sm font-medium text-slate-700 mb-1">
              Họ và tên
            </label>
            <input
              id="profile_fullname"
              type="text"
              required
              disabled={nameLoading}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>

          <Button
            type="submit"
            disabled={nameLoading}
            className="bg-slate-900 hover:bg-slate-800 text-white"
          >
            {nameLoading ? "Đang lưu..." : "Lưu thay đổi"}
          </Button>
        </form>
      </div>

      {/* Đổi mật khẩu */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Đổi mật khẩu
        </h2>
        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          {pwdSuccess && (
            <div className="rounded-md bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-800">
              Đổi mật khẩu thành công. Các phiên đăng nhập khác đã được thu hồi.
            </div>
          )}
          {pwdError && (
            <div role="alert" className="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-800">
              {pwdError}
            </div>
          )}

          <div>
            <label htmlFor="old_pwd" className="block text-sm font-medium text-slate-700 mb-1">
              Mật khẩu hiện tại
            </label>
            <input
              id="old_pwd"
              type="password"
              required
              disabled={pwdLoading}
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>

          <div>
            <label htmlFor="new_pwd" className="block text-sm font-medium text-slate-700 mb-1">
              Mật khẩu mới
            </label>
            <input
              id="new_pwd"
              type="password"
              required
              disabled={pwdLoading}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
              placeholder="Tối thiểu 15 ký tự"
            />
          </div>

          <div>
            <label htmlFor="confirm_pwd" className="block text-sm font-medium text-slate-700 mb-1">
              Xác nhận mật khẩu mới
            </label>
            <input
              id="confirm_pwd"
              type="password"
              required
              disabled={pwdLoading}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>

          <Button
            type="submit"
            disabled={pwdLoading}
            className="bg-slate-900 hover:bg-slate-800 text-white"
          >
            {pwdLoading ? "Đang xử lý..." : "Đổi mật khẩu"}
          </Button>
        </form>
      </div>
    </div>
  );
}
