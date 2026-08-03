"""메트릭 배선 (E9) — 숫자가 쥐어지고, 읽히고, 고객을 새지 않는다.

관측 패키지는 계약 요청 §4·§9 로 배선을 요청만 해 두었다: 기본 싱크는 Null 이었고
요청 기록 미들웨어도 없었다 — 계기판이 있는데 선이 안 이어진 상태. 이 시험이
지키는 것:

1. 앱이 실싱크를 설치하고, 요청 하나가 카운터·지연 분포로 남는다.
2. 라벨의 경로는 **템플릿**이다 — 해석된 경로가 들어가면 고객 식별자가 접근통제
   없는 저장소로 흘러간다. (이 FastAPI 판에서 scope["route"].path 는 마운트
   접두사 없는 하위 경로다 — "/health". 템플릿이라는 성질은 같다.)
3. /metrics 가 그 숫자를 Prometheus 텍스트로 내보낸다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.api.metrics import METRICS_SINK, render_prometheus
from veo.observability import InMemoryMetricSink


class TestTheWiring:
    def test_one_request_lands_in_the_sink_under_the_route_template(self) -> None:
        app = create_app()
        before = METRICS_SINK.counter_value(
            "veo_http_requests_total", route="/health", method="GET", status_class="2xx"
        )
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200

        after = METRICS_SINK.counter_value(
            "veo_http_requests_total", route="/health", method="GET", status_class="2xx"
        )
        assert after == before + 1

    def test_the_exporter_serves_what_the_sink_holds(self) -> None:
        app = create_app()
        with TestClient(app) as client:
            client.get("/api/health")
            response = client.get("/api/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "veo_http_requests_total" in response.text
        assert 'route="/health"' in response.text
        # 싱크 자체의 손실 계수도 노출된다 — 조용히 버려진 시리즈는 없는 것과 다르다.
        assert "veo_metrics_dropped_series_total" in response.text


class TestTheRenderer:
    def test_counters_gauges_and_histograms_render_with_escaped_labels(self) -> None:
        sink = InMemoryMetricSink()
        sink.increment("veo_x_total", 2.0, {"route": '/a"b\\c'})
        sink.gauge("veo_depth", 3.0, {"queue": "scan"})
        sink.observe("veo_wait_ms", 10.0)
        sink.observe("veo_wait_ms", 30.0)

        text = render_prometheus(sink.snapshot())

        assert 'veo_x_total{route="/a\\"b\\\\c"} 2.0' in text
        assert 'veo_depth{queue="scan"} 3.0' in text
        # 분포는 버킷 없이 네 값 — 있는 것을 있는 그대로.
        assert "veo_wait_ms_count 2.0" in text
        assert "veo_wait_ms_sum 40.0" in text
        assert "veo_wait_ms_min 10.0" in text
        assert "veo_wait_ms_max 30.0" in text
