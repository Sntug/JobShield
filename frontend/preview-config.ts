import type { NextConfig } from "next";

export function previewConfig(env: Record<string, string | undefined>): Partial<NextConfig> {
  const isPreview = env.VERCEL_ENV === "preview";
  if (!isPreview && (env.VERCEL_ENV || !env.API_PROXY_TARGET)) return {};
  const id = env.VERCEL_GIT_PULL_REQUEST_ID || "";
  if (isPreview && id && !/^[1-9][0-9]{0,9}$/.test(id)) {
    throw new Error("Invalid VERCEL_GIT_PULL_REQUEST_ID; refusing to select a backend.");
  }
  let target = id ? `https://jobshield-pr-${id}.onrender.com` : null;
  if (!isPreview) {
    if (!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]{1,5}$/.test(env.API_PROXY_TARGET || "")) {
      throw new Error("API_PROXY_TARGET is only supported for local loopback integration tests.");
    }
    target = env.API_PROXY_TARGET!;
  }
  return {
    // Preview routing comes from PR metadata, never an old branch-specific override.
    env: { NEXT_PUBLIC_API_BASE_URL: "" },
    rewrites: async () => [
      { source: "/api/v1/:path*", destination: target ? `${target}/api/v1/:path*` : "/api/preview-unavailable" },
      { source: "/ready", destination: target ? `${target}/ready` : "/api/preview-unavailable" },
    ],
  };
}
