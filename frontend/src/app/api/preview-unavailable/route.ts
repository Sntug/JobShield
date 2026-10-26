function unavailable() {
  return Response.json({
    status: "not_ready", database: "unconfigured",
    detail: { code: "PR_NOT_ASSOCIATED", message_vi: "Nhánh chưa được gắn với Pull Request. Hãy mở PR và triển khai lại Preview." },
  }, { status: 503, headers: { "Cache-Control": "no-store" } });
}

export const GET = unavailable;
export const POST = unavailable;
export const OPTIONS = unavailable;
