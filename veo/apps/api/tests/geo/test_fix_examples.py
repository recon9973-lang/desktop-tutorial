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
import re
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
    def test_no_invented_fact_is_shipped(self, check_id: str) -> None:
        """**이 시험이 없어서 지어낸 사실이 운영까지 나갔다.**

        실측 2026-08-08 — v0.3.62 로 배포된 예시 안에 내가 만든 값이 들어 있었다:

            "붓기는 보통 2~3일째 가장 심하고 5~7일 안에 대부분 가라앉습니다"
            "국산 임플란트 100만원~ / 수입 150만원~ / 3~4개월"
            "임플란트 10년 생존율은 약 95%로 보고됩니다 (대한구강악안면학회, 2024)"
            "환자 412명을 대상으로 … 검진에 오지 않은 37명은 제외했습니다"
            "들안로 209, 2층 · 대구광역시 수성구 · 053-000-0000"

        전부 출처가 없다. 그런데 화면에는 **"복사해서 붙여넣으세요"** 라고 적혀 있다.
        병원이 그대로 올리면 (1) 우리가 지어낸 비급여 진료비를 게시하고,
        (2) 하지 않은 조사를 자기 이름으로 발표하고, (3) 없는 연구를 실재하는 학회가
        발표한 것처럼 만든다. 그리고 **AI 가 그것을 인용한다** — 우리가 파는 것이
        정확히 그것이다.

        기존 시험은 실제 상호와 `example.com` 만 막았다. 지어낸 **사실**은 막을
        생각을 안 했다. 내가 지어낸 줄 몰랐기 때문이다.

        규칙: 예시는 **구조를 가르치고 내용은 비운다.** 금액·기간·수량·백분율·날짜·
        주소·전화가 나오려면 `[ ]` 로 묶여 있어야 한다 — 그러면 그대로 붙여넣었을 때
        동작하지 않는 것이 눈에 보인다.
        """
        example = code_example_for(check_id)
        if example is None:
            pytest.skip("예시가 없는 검사")

        # `[...]` 안은 자리표시자다. 그것을 지우고 남은 곳에 사실이 있으면 지어낸 것이다.
        outside = re.sub(r"\[[^\]]*\]", "", example)

        facts = re.findall(
            r"\d[\d,]*\s*(?:만원|원|명|일째|개월|주일|년|%)"  # 금액·기간·수량·비율
            r"|\d{4}-\d{2}-\d{2}"  # 날짜
            r"|\d{2,4}-\d{3,4}-\d{4}"  # 전화번호
            r"|[가-힣]+(?:로|길)\s*\d+",  # 도로명 주소
            outside,
        )

        assert not facts, (
            f"{check_id} 의 예시에 출처 없는 사실이 있습니다: {facts}. "
            "예시는 구조만 가르치고 내용은 `[대괄호]` 자리표시자로 비웁니다 — "
            "금액·기간·통계·주소는 병원 것이지 우리 것이 아닙니다. "
            "docs/CORRECTIONS.md 참조."
        )

    @pytest.mark.parametrize("check_id", sorted(_spec_check_ids()))
    def test_no_named_institution_is_cited(self, check_id: str) -> None:
        """실재하는 기관 이름을 출처로 적으면, 하지 않은 발표를 그 기관이 한 것이 된다.

        실측: "대한구강악안면임플란트학회, 2024" 를 예시 출처로 적어 배포했다.
        그런 발표가 있는지 확인한 적이 없다.
        """
        example = code_example_for(check_id)
        if example is None:
            pytest.skip("예시가 없는 검사")

        outside = re.sub(r"\[[^\]]*\]", "", example)
        institutions = re.findall(r"[가-힣]{2,}(?:학회|협회|재단|연구원|청|부|처)", outside)

        assert not institutions, (
            f"{check_id} 의 예시가 실재 기관을 출처로 인용합니다: {institutions}. "
            "확인하지 않은 인용은 그 기관이 하지 않은 발표를 한 것으로 만듭니다."
        )

    @pytest.mark.parametrize("check_id", sorted(_spec_check_ids()))
    def test_placeholders_are_visibly_placeholders(self, check_id: str) -> None:
        """자리표시자는 **그대로 붙여넣으면 동작하지 않는다는 것이 눈에 보여야** 한다.
        `https://example.com` 처럼 진짜 같아 보이는 값은 그대로 올라간다."""
        example = code_example_for(check_id)
        if example is None:
            pytest.skip("예시가 없는 검사")

        assert "example.com" not in example
        assert "localhost" not in example
