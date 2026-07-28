import { describe, expect, it, vi } from "vitest";

import { createVeoClient, VeoApiError } from "./client.js";

function jsonResponse(body: unknown, status = 200, requestId = "req-123"): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Request-Id": requestId },
  });
}

const meta = {
  request_id: "req-123",
  generated_at: "2026-07-28T00:00:00Z",
  sources: [],
};

describe("createVeoClient", () => {
  it("unwraps the envelope and surfaces the correlation id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: {
          status: "ok",
          app_name: "VEO",
          tagline: "SEO · GEO · Naver Keyword Intelligence Platform",
          developed_by: "VENOM",
          methodology_by: "VEO-LAB",
          environment: "local",
          version: "0.1.0",
        },
        error: null,
        meta,
      }),
    );

    const client = createVeoClient({ baseUrl: "http://api.test/", fetch: fetchMock });
    const result = await client.health();

    expect(result.data.developed_by).toBe("VENOM");
    expect(result.data.methodology_by).toBe("VEO-LAB");
    expect(result.requestId).toBe("req-123");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws a structured error carrying the machine-readable code", async () => {
    // A Response body can be read once, so build a fresh one per call.
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        jsonResponse(
          {
            data: null,
            error: {
              code: "VALIDATION_FAILED",
              message: "입력값이 올바르지 않습니다.",
              field_errors: [
                { field: "url", code: "invalid", message: "URL 형식이 아닙니다." },
              ],
              retryable: false,
            },
            meta,
          },
          422,
        ),
      ),
    );

    const client = createVeoClient({ baseUrl: "http://api.test", fetch: fetchMock });

    await expect(client.listScoringSpecs()).rejects.toBeInstanceOf(VeoApiError);
    await expect(client.listScoringSpecs()).rejects.toMatchObject({
      code: "VALIDATION_FAILED",
      status: 422,
      retryable: false,
      requestId: "req-123",
    });
  });

  it("sends a correlation id when one is configured", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: { specs: [] }, error: null, meta }));

    const client = createVeoClient({
      baseUrl: "http://api.test",
      fetch: fetchMock,
      requestId: () => "trace-abc",
    });
    await client.listScoringSpecs();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-Request-Id"]).toBe("trace-abc");
  });

  it("treats a 200 with an empty payload as a failure rather than silently returning null", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: null, error: null, meta }));

    const client = createVeoClient({ baseUrl: "http://api.test", fetch: fetchMock });
    await expect(client.health()).rejects.toBeInstanceOf(VeoApiError);
  });

  it("serialises an evaluate request as JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: { spec_id: "x" }, error: null, meta }));

    const client = createVeoClient({ baseUrl: "http://api.test", fetch: fetchMock });
    await client.evaluateScore({
      spec_id: "veo.seo.readiness",
      spec_version: "1.0.0",
      outcomes: [{ check_id: "seo.http.status_ok", status: "PASS", confidence: 1 }],
    } as never);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/api/scoring/evaluate");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string).spec_id).toBe("veo.seo.readiness");
  });
});
