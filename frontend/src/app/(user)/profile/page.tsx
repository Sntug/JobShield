"use client";

import React from "react";
import { ProfileForm } from "@/components/profile/profile-form";
import { useAuth } from "@/hooks/use-auth";
import { changePassword, updateProfile } from "@/lib/api-client";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();

  if (!user) return null;

  const handleUpdateName = async (name: string) => {
    await updateProfile(name);
    await refreshUser();
  };

  const handleChangePassword = async (oldPwd: string, newPwd: string) => {
    await changePassword(oldPwd, newPwd);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Hồ sơ & Bảo mật
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Quản lý thông tin cá nhân và thiết lập mật khẩu đăng nhập.
        </p>
      </div>

      <ProfileForm
        user={user}
        onUpdateName={handleUpdateName}
        onChangePassword={handleChangePassword}
      />
    </div>
  );
}
