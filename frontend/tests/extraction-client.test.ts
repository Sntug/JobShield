import { afterEach, expect, it, vi } from "vitest";
import { extractFromImage } from "@/lib/api-client";

afterEach(() => vi.unstubAllGlobals());

it("uploads the image bytes with the image MIME type", async () => {
  let request: RequestInit | undefined;
  vi.stubGlobal("fetch", async (_url: string, options: RequestInit) => {
    request = options;
    return new Response(JSON.stringify({ success: false, text: null, failure_vi: "Ảnh không có chữ." }));
  });
  const image = new File(["image-bytes"], "job.png", { type: "image/png" });
  await extractFromImage(image);
  expect(new Headers(request?.headers).get("Content-Type")).toBe("image/png");
  expect(request?.body).toBe(image);
  expect(request?.cache).toBe("no-store");
});
