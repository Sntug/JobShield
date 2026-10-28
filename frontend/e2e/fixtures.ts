import { createHash } from "node:crypto";
import { test as base, expect, type TestInfo } from "@playwright/test";

function clientHeaders(baseURL: string | undefined, info: TestInfo) {
  if (!baseURL || !["localhost", "127.0.0.1"].includes(new URL(baseURL).hostname)) {
    throw new Error("Synthetic client identities are only allowed on loopback E2E servers");
  }
  const client = createHash("sha256").update(`${info.testId}:${info.retry}`).digest("hex").slice(0, 24);
  return { "x-jobshield-e2e-client": client };
}

// Supply identities only to the loopback test proxy; direct CORS requests stay real.
export const test = base.extend({
  context: async ({ context, baseURL }, provide, info) => {
    const headers = clientHeaders(baseURL, info);
    await context.route(`${baseURL}/api/**`, route => route.continue({
      headers: { ...route.request().headers(), ...headers },
    }));
    await provide(context);
  },
  request: async ({ playwright, baseURL }, provide, info) => {
    const request = await playwright.request.newContext({ baseURL, extraHTTPHeaders: clientHeaders(baseURL, info) });
    try { await provide(request); }
    finally { await request.dispose(); }
  },
});
export { expect };
