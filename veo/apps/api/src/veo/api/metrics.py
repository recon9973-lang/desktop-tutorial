"""프로세스 메트릭의 노출 — 관측 패키지 계약 요청 §9 의 이행 (E9).

관측 패키지는 익스포터 의존성(`prometheus_client` 등)을 갖지 않겠다고 못박았다.
그래서 여기서는 **의존성 없이** InMemoryMetricSink 의 스냅샷을 Prometheus 텍스트
형식으로 그린다 — 시리즈 이름은 이미 그 규약(`veo_*_total`)으로 지어져 있다.

분포는 버킷이 없으므로 히스토그램이 아니라 네 개의 게이지(`*_count`·`*_sum`·
`*_min`·`*_max`)로 나간다 — 있는 것을 있는 그대로. 백분위가 필요해지면 그때
버킷 있는 익스포터를 이 프로토콜 뒤에 끼우면 되고, 호출 지점은 바뀌지 않는다.

싱크 자체의 손실도 함께 노출한다(`veo_metrics_dropped_series_total` 등) — 카디널리티
상한에 걸려 버려진 시리즈가 있는데 그래프가 조용하면, 없는 것과 안 보이는 것이
섞인다.

테넌트 식별자는 여기 없다 — record_http_request 가 조직을 해시로만 받는 것이 그
이유였고, 이 화면은 그 설계 덕에 인증 없이도 고객 목록을 새지 않는다.
"""

from __future__ import annotations

from typing import Final

from veo.observability import InMemoryMetricSink, MetricsSnapshot

__all__ = ["METRICS_SINK", "render_prometheus"]

#: 프로세스 전역 실싱크. create_app 이 set_metric_sink 로 설치하고, /metrics 가 읽는다.
METRICS_SINK: Final = InMemoryMetricSink()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _series(name: str, labels: tuple[tuple[str, str], ...], value: float) -> str:
    if not labels:
        return f"{name} {value}"
    rendered = ",".join(f'{key}="{_escape(item)}"' for key, item in labels)
    return f"{name}{{{rendered}}} {value}"


def render_prometheus(snapshot: MetricsSnapshot) -> str:
    lines: list[str] = []

    for name, labels, value in snapshot.counters:
        lines.append(_series(name, labels, value))
    for name, labels, value in snapshot.gauges:
        lines.append(_series(name, labels, value))
    for name, labels, summary in snapshot.histograms:
        lines.append(_series(f"{name}_count", labels, float(summary.count)))
        lines.append(_series(f"{name}_sum", labels, summary.total))
        lines.append(_series(f"{name}_min", labels, summary.minimum))
        lines.append(_series(f"{name}_max", labels, summary.maximum))

    lines.append(_series("veo_metrics_dropped_series_total", (), float(snapshot.dropped_series)))
    lines.append(
        _series("veo_metrics_rejected_samples_total", (), float(snapshot.rejected_samples))
    )
    return "\n".join(lines) + "\n"
