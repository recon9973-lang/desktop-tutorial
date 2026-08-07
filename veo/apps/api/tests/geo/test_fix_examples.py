"""GEO 이슈에 **붙여넣을 수 있는 코드**가 실려 나가는가.

실측 2026-08-07 — 운영 GEO 리포트의 `fix_example` 은 37개 검사 중 **하나만** 채워져
있었다(`access.search_bots_allowed`). SEO 는 같은 자리에 30개가 있었다. 두 화면이
나란히 놓이는데(SEO|GEO 전환기) 한쪽만 코드가 나오면, 읽는 사람은 GEO 쪽에 고칠 방법이
없다고 읽는다. 실제로는 방법이 있는데 문장으로만 적혀 있었다.

칸은 처음부터 있었다(`GeoIssuePayload.fix_example`). 채우는 코드가 없었을 뿐이다 —
부를 수 없는 기능은 없는 기능이다(0-E).
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from veo.collect.contract import IssueDraft
from veo.geo.fix_examples import code_example_for
from veo.geo.payload import _issue_payload
from veo.seo.fix_examples import BRAND_PLACEHOLDER


def _spec_check_ids() -> set[str]:
    path = Path(sorted(glob.glob("packages/scoring-specs/specs/veo.geo.readiness/*.yaml"))[-1])
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        check["id"] for category in document["categories"] for check in category["checks"]
    }


def _draft(check_id: str, *, fix_example: str | None = None) -> IssueDraft:
    return IssueDraft(
        check_id=check_id,
        title_ko="제목",
        summary_ko="요약",
        remediation_ko="조치",
        remediation_owner="DEVELOPER",
        business_impact_ko="영향",
        affected_urls=("https://a.example/",),
        evidence_ids=(),
        fix_example=fix_example,
        reverification_note_ko="재확인",
    )


class TestTheRegistryMatchesTheSpec:
    def test_every_registered_id_exists_in_the_spec(self) -> None:
        """명세에 없는 검사에 예시를 달아 두면 **영원히 안 나온다.**

        오타 하나가 조용히 죽은 항목을 만든다. 화면에는 아무 일도 안 일어나므로
        아무도 모른다.
        """
        from veo.geo.fix_examples import _EXAMPLES

        unknown = set(_EXAMPLES) - _spec_check_ids()

        assert not unknown, f"명세에 없는 검사에 예시가 달려 있습니다: {sorted(unknown)}"

    def test_enough_checks_are_covered_to_be_useful(self) -> None:
        """전부일 필요는 없다 — 정답 코드가 하나로 정해지는 것만 싣는 것이 이 등록부의
        규칙이다. 다만 한두 개만 있으면 있으나 마나다."""
        covered = [cid for cid in _spec_check_ids() if code_example_for(cid)]

        assert len(covered) >= 15, f"예시가 {len(covered)}개뿐입니다"


class TestTheExampleReachesTheIssue:
    def test_a_registered_check_gets_its_example(self) -> None:
        """이것이 깨져 있던 자리다. 칸은 있는데 채우는 코드가 없었다."""
        issue = _issue_payload(_draft("geo.entity.organization_identified"))

        assert issue.fix_example is not None
        assert "MedicalClinic" in issue.fix_example

    def test_the_collector_wins_over_the_registry(self) -> None:
        """수집기가 만든 코드에는 **그 사이트에서 실제로 잰 값**이 들어 있다.
        표준 예시로 덮으면 현장 값이 사라진다."""
        issue = _issue_payload(
            _draft("geo.entity.organization_identified", fix_example="현장에서 만든 코드")
        )

        assert issue.fix_example == "현장에서 만든 코드"

    def test_an_unregistered_check_stays_empty(self) -> None:
        """사이트마다 답이 다른 항목에 코드를 지어내면, 담당자는 **틀린 코드를 확신을
        가지고** 붙여넣는다. 빈 것이 틀린 것보다 낫다."""
        issue = _issue_payload(_draft("geo.external.independent_sources_exist"))

        assert issue.fix_example is None


class TestTheBrandNameIsSubstitutedNotInvented:
    def test_a_known_brand_replaces_the_placeholder(self) -> None:
        issue = _issue_payload(
            _draft("geo.entity.organization_identified"), "베놈애드"
        )

        assert issue.fix_example is not None
        assert "베놈애드" in issue.fix_example
        assert BRAND_PLACEHOLDER not in issue.fix_example

    def test_without_a_brand_the_placeholder_stays(self) -> None:
        """도메인이나 제목에서 상호를 추측해 넣으면 **틀린 이름을 확신을 가지고**
        붙여넣게 만든다. 그것은 자리표시자보다 나쁘다."""
        issue = _issue_payload(_draft("geo.entity.organization_identified"), None)

        assert issue.fix_example is not None
        assert BRAND_PLACEHOLDER in issue.fix_example


class TestTheExamplesAreSafeToPaste:
    @pytest.mark.parametrize("check_id", sorted(_spec_check_ids()))
    def test_no_real_business_name_is_baked_in(self, check_id: str) -> None:
        """예전에 SEO 쪽 예시에 가상의 병원 이름이 박혀 있었다. 복사해 쓰라고 내놓은
        코드에 **남의 상호**가 들어 있으니, 읽는 사람은 그것이 자기 사이트에서 측정된
        값인 줄 알았다. 같은 실수를 여기서 반복하지 않는다."""
        example = code_example_for(check_id)
        if example is None:
            pytest.skip("예시가 없는 검사")

        for banned in ("온담의원", "베놈애드", "venomad"):
            assert banned not in example, f"{check_id} 에 실제 상호가 박혀 있습니다"

    @pytest.mark.parametrize("check_id", sorted(_spec_check_ids()))
    def test_placeholders_are_visibly_placeholders(self, check_id: str) -> None:
        """자리표시자는 **그대로 붙여넣으면 동작하지 않는다는 것이 눈에 보여야** 한다.
        `https://example.com` 처럼 진짜 같아 보이는 값은 그대로 올라간다."""
        example = code_example_for(check_id)
        if example is None:
            pytest.skip("예시가 없는 검사")

        assert "example.com" not in example
        assert "localhost" not in example
