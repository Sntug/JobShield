import { createHash } from "node:crypto";
import { test as base, expect } from "@playwright/test";

// Each test represents a separate client; the loopback-only proxy supplies its IP.
export const test = base.extend({
  extraHTTPHeaders: async ({ baseURL }, use, info) => {
    if (!baseURL || !["localhost", "127.0.0.1"].includes(new URL(baseURL).hostname)) {
      throw new Error("Synthetic client identities are only allowed on loopback E2E servers");
    }
    const client = createHash("sha256").update(`${info.testId}:${info.retry}`).digest("hex").slice(0, 24);
    await use({ "x-jobshield-e2e-client": client });
  },
});
export { expect };
