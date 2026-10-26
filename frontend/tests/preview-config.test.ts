import { describe, expect, it } from "vitest";
import { previewConfig } from "../preview-config";
import { GET, POST } from "../src/app/api/preview-unavailable/route";

describe("Preview backend selection", () => {
  it.each(["8", "9"])("ignores stale manual API override for PR %s", async (id) => {
    const config = previewConfig({ VERCEL_ENV: "preview", VERCEL_GIT_PULL_REQUEST_ID: id, NEXT_PUBLIC_API_BASE_URL: "https://jobshield-pr-7.onrender.com" });
    expect(config.env?.NEXT_PUBLIC_API_BASE_URL).toBe("");
    expect(await config.rewrites?.()).toEqual([
      { source: "/api/v1/:path*", destination: `https://jobshield-pr-${id}.onrender.com/api/v1/:path*` },
      { source: "/ready", destination: `https://jobshield-pr-${id}.onrender.com/ready` },
    ]);
  });
  it("fails closed before a PR is associated", async () => {
    const config = previewConfig({ VERCEL_ENV: "preview", NEXT_PUBLIC_API_BASE_URL: "https://production.example" });
    expect(config.env?.NEXT_PUBLIC_API_BASE_URL).toBe("");
    expect(await config.rewrites?.()).toEqual([
      { source: "/api/v1/:path*", destination: "/api/preview-unavailable" },
      { source: "/ready", destination: "/api/preview-unavailable" },
    ]);
  });
  it.each(["0", "08", "-1", "8.example.com", "8/../9", "12345678901"])("rejects malformed metadata %s", (id) => {
    expect(() => previewConfig({ VERCEL_ENV: "preview", VERCEL_GIT_PULL_REQUEST_ID: id })).toThrow();
  });
  it.each(["production", "development", undefined])("leaves %s behavior intact", (environment) => {
    expect(previewConfig({ VERCEL_ENV: environment, NEXT_PUBLIC_API_BASE_URL: "https://production.example" })).toEqual({});
  });
  it("supports the same proxy path against an explicit loopback API in integration tests", async () => {
    const config = previewConfig({ API_PROXY_TARGET: "http://127.0.0.1:8000" });
    expect(config.env?.NEXT_PUBLIC_API_BASE_URL).toBe("");
    expect(await config.rewrites?.()).toEqual([
      { source: "/api/v1/:path*", destination: "http://127.0.0.1:8000/api/v1/:path*" },
      { source: "/ready", destination: "http://127.0.0.1:8000/ready" },
    ]);
  });
  it("does not allow the integration override to redirect Vercel Preview", async () => {
    const config = previewConfig({ VERCEL_ENV: "preview", VERCEL_GIT_PULL_REQUEST_ID: "9", API_PROXY_TARGET: "https://attacker.example" });
    expect(JSON.stringify(await config.rewrites?.())).toContain("jobshield-pr-9.onrender.com");
  });
  it("rejects an external integration override", () => {
    expect(() => previewConfig({ API_PROXY_TARGET: "https://attacker.example" })).toThrow();
  });
  it("returns actionable uncached JSON without PR metadata for GET and POST", async () => {
    for (const response of [GET(), POST()]) {
      expect(response.status).toBe(503);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect((await response.json()).detail.code).toBe("PR_NOT_ASSOCIATED");
    }
  });
});
