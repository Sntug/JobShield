import { expect, test } from "./fixtures";

test("same-origin proxy preserves schema readiness, validation and trace headers", async ({ request }) => {
  const ready = await request.get("/ready");
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toMatchObject({ status: "ready", database: "connected", schema: "current" });
  expect(ready.headers()["cache-control"]).toContain("no-store");
  expect(ready.headers()["x-request-id"]).toBeTruthy();
  if (process.env.GIT_COMMIT) expect(ready.headers()["x-commit-sha"]).toBe(process.env.GIT_COMMIT.slice(0, 7));

  const invalid = await request.post("/api/v1/verifications", { data: {} });
  expect(invalid.status()).toBe(422);
  expect((await invalid.json()).detail.code).toBe("NO_INPUT_PROVIDED");
  expect(invalid.headers()["cache-control"]).toContain("no-store");
  expect(invalid.headers()["x-request-id"]).toBeTruthy();
});

test("real Next proxy preserves upstream 503 and 429 with retry and privacy headers", async ({ request }) => {
  for (const status of [503, 429]) {
    const response = await request.get(`/api/v1/__proxy-fixture/${status}`);
    expect(response.status()).toBe(status);
    expect(response.headers()["cache-control"]).toBe("no-store");
    expect(response.headers()["x-request-id"]).toBe("proxy-fixture-trace");
    expect((await response.json()).detail.code).toBe(`UPSTREAM_${status}`);
    if (status === 429) expect(response.headers()["retry-after"]).toBe("17");
  }
});
