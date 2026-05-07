from pathlib import Path

from services.detail_replay import load_replay_cases, run_replay_case


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "detail_replay"


def test_detail_replay_cases_cover_core_channels():
    cases = load_replay_cases(FIXTURE_DIR / "manifest.json")

    assert {case.channel_code for case in cases} == {"weibo", "36kr", "csdn"}


def test_detail_replay_cases_extract_expected_content():
    cases = load_replay_cases(FIXTURE_DIR / "manifest.json")

    for case in cases:
        result = run_replay_case(case)
        assert result.status in {"complete", "partial"}, case.name
        for term in case.expected_terms:
            assert term in result.content, case.name
        for term in case.forbidden_terms:
            assert term not in result.content, case.name
