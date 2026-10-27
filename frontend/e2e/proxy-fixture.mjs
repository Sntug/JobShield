// Local-only upstream: real API requests pass through; two paths exercise proxy error headers.
import { createServer } from "node:http";

const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
const port = Number(process.env.PROXY_FIXTURE_PORT);
if (!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]{1,5}$/.test(target) || !Number.isInteger(port) || port < 1024 || port > 65535) {
  throw new Error("Proxy fixture must use explicit loopback endpoints");
}

createServer(async (req, res) => {
  if (req.url === "/fixture-ready") {
    res.writeHead(200).end("ready");
    return;
  }
  const match = /^\/api\/v1\/__proxy-fixture\/(503|429)$/.exec(req.url || "");
  if (match) {
    const status = Number(match[1]);
    res.writeHead(status, {
      "Content-Type": "application/json", "Cache-Control": "no-store",
      "X-Request-ID": "proxy-fixture-trace", ...(status === 429 ? { "Retry-After": "17" } : {}),
    }).end(JSON.stringify({ detail: { code: `UPSTREAM_${status}` } }));
    return;
  }
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const headers = {};
    for (const key of ["content-type", "accept", "authorization", "x-guest-session-token", "x-request-id", "origin"]) {
      if (req.headers[key]) headers[key] = req.headers[key];
    }
    const response = await fetch(target + req.url, {
      method: req.method, headers,
      body: ["GET", "HEAD"].includes(req.method) ? undefined : Buffer.concat(chunks),
      redirect: "manual", signal: AbortSignal.timeout(30_000),
    });
    const resultHeaders = Object.fromEntries(response.headers);
    for (const key of ["content-encoding", "content-length", "transfer-encoding"]) delete resultHeaders[key];
    res.writeHead(response.status, resultHeaders).end(Buffer.from(await response.arrayBuffer()));
  } catch {
    res.writeHead(502, { "Content-Type": "application/json" }).end('{"error":"Local test upstream unavailable"}');
  }
}).listen(port, "127.0.0.1");
