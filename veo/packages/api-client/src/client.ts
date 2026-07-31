/**
 * Typed VEO API client.
 *
 * Every type here comes from `schema.d.ts`, which is generated from
 * `apps/api/openapi.json`. Nothing in this file hand-writes a response shape, so an API
 * change that is not reflected in the contract fails at compile time rather than in
 * production.
 */
import type { components, paths } from "./schema.js";

type Schemas = components["schemas"];

export type ApiError = Schemas["ApiError"];
export type ResponseMeta = Schemas["ResponseMeta"];
export type HealthPayload = Schemas["HealthPayload"];
export type ProviderStatusPayload = Schemas["ProviderStatusPayload"];
export type SpecListPayload = Schemas["SpecListPayload"];
export type SpecSummary = Schemas["SpecSummary"];
export type SpecDetail = Schemas["SpecDetail"];
export type SeverityVocabularyPayload = Schemas["SeverityVocabularyPayload"];
export type SeverityTermPayload = Schemas["SeverityTermPayload"];
export type ScorePayload = Schemas["ScorePayload"];
export type EvaluateScoreRequest = Schemas["EvaluateScoreRequest"];
export type CheckOutcomeInput = Schemas["CheckOutcomeInput"];

export const REQUEST_ID_HEADER = "X-Request-Id";

/** A structured failure. Carries the machine-readable code, never a bare string. */
export class VeoApiError extends Error {
  readonly code: ApiError["code"];
  readonly status: number;
  readonly fieldErrors: ApiError["field_errors"];
  readonly retryable: boolean;
  readonly retryAfterSeconds: number | null;
  readonly requestId: string | null;

  constructor(status: number, error: ApiError, requestId: string | null) {
    super(error.message);
    this.name = "VeoApiError";
    this.status = status;
    this.code = error.code;
    this.fieldErrors = error.field_errors;
    this.retryable = error.retryable;
    this.retryAfterSeconds = error.retry_after_seconds ?? null;
    this.requestId = requestId;
  }
}

/** A successful response, with the metadata that makes the payload interpretable. */
export interface VeoResult<T> {
  data: T;
  meta: ResponseMeta;
  requestId: string | null;
}

export interface VeoClientOptions {
  baseUrl: string;
  /** Injected so tests never touch the network. */
  fetch?: typeof globalThis.fetch;
  /** Correlates a browser action with server logs. */
  requestId?: () => string;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

interface Envelope<T> {
  data: T | null;
  error: ApiError | null;
  meta: ResponseMeta;
}

export function createVeoClient(options: VeoClientOptions) {
  const baseUrl = options.baseUrl.replace(/\/+$/, "");
  const doFetch = options.fetch ?? globalThis.fetch;

  async function request<T>(
    path: string,
    init: { method: "GET" | "POST"; body?: unknown } = { method: "GET" },
  ): Promise<VeoResult<T>> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...options.headers,
    };
    if (init.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (options.requestId) {
      headers[REQUEST_ID_HEADER] = options.requestId();
    }

    const response = await doFetch(`${baseUrl}${path}`, {
      method: init.method,
      headers,
      ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
      ...(options.signal ? { signal: options.signal } : {}),
    });

    const requestId = response.headers.get(REQUEST_ID_HEADER);
    const envelope = (await response.json()) as Envelope<T>;

    if (!response.ok || envelope.error !== null) {
      const error: ApiError = envelope.error ?? {
        code: "INTERNAL_ERROR",
        message: "요청을 처리하지 못했습니다.",
        field_errors: [],
        retryable: true,
      };
      throw new VeoApiError(response.status, error, requestId);
    }

    if (envelope.data === null) {
      throw new VeoApiError(
        response.status,
        {
          code: "INTERNAL_ERROR",
          message: "응답 본문이 비어 있습니다.",
          field_errors: [],
          retryable: true,
        },
        requestId,
      );
    }

    return { data: envelope.data, meta: envelope.meta, requestId };
  }

  return {
    health(): Promise<VeoResult<HealthPayload>> {
      return request<HealthPayload>("/api/health");
    },

    /** Reports which external providers are actually connected. */
    providers(): Promise<VeoResult<ProviderStatusPayload>> {
      return request<ProviderStatusPayload>("/api/providers");
    },

    listScoringSpecs(): Promise<VeoResult<SpecListPayload>> {
      return request<SpecListPayload>("/api/scoring/specs");
    },

    getScoringSpec(specId: string, version: string): Promise<VeoResult<SpecDetail>> {
      return request<SpecDetail>(
        `/api/scoring/specs/${encodeURIComponent(specId)}/${encodeURIComponent(version)}`,
      );
    },

    /** Reproduce a score from published inputs against a published specification. */
    evaluateScore(body: EvaluateScoreRequest): Promise<VeoResult<ScorePayload>> {
      return request<ScorePayload>("/api/scoring/evaluate", { method: "POST", body });
    },
  };
}

export type VeoClient = ReturnType<typeof createVeoClient>;
export type { components, paths };
