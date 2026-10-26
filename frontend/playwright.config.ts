import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.PLAYWRIGHT_PORT || 3000);
if (!Number.isInteger(port) || port < 1024 || port > 65534) throw new Error("Invalid PLAYWRIGHT_PORT");
const baseURL = `http://127.0.0.1:${port}`;
const upstreamURL = `http://127.0.0.1:${port + 1}`;

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [{
    command: "node e2e/proxy-fixture.mjs",
    env: { PROXY_FIXTURE_PORT: String(port + 1), API_PROXY_TARGET: process.env.API_PROXY_TARGET || "http://127.0.0.1:8000" },
    url: `${upstreamURL}/fixture-ready`,
    reuseExistingServer: false,
  }, {
    command: `npm run build && npm run start -- --hostname 127.0.0.1 --port ${port}`,
    env: { API_PROXY_TARGET: upstreamURL },
    url: baseURL,
    reuseExistingServer: false,
    timeout: 180_000,
  }],
});
