import io
import stat

import pytest
from werkzeug.datastructures import FileStorage

from app.v2.decision import DecisionIntelligenceService
from app.v2.extraction import ExtractionService
from app.v2.report import ForecastReportService
from app.v2.research_ingestion import ResearchIngestionService
from app.v2.schemas import V2RunState
from app.v2.storage import V2Storage


def _claims(markdown: str):
    documents = ResearchIngestionService(chunk_size=100_000, chunk_overlap=0).ingest_inline_documents(
        [{"filename": "report.md", "text": markdown}]
    )
    return ExtractionService().extract_claims(documents)


def _urls(claim):
    return {citation.url for citation in claim.citations if citation.url}


def test_same_paragraph_markdown_links_bind_only_to_nearest_statement():
    alpha = "https://evidence.example/alpha"
    beta = "https://evidence.example/beta"
    markdown = (
        "Alpha reported that revenue growth increased by 18 percent. "
        f"[Alpha evidence]({alpha}) "
        "Beta reported that debt risk increased after the delay. "
        f"[Beta evidence]({beta})"
    )

    claims = _claims(markdown)
    alpha_claim = next(claim for claim in claims if claim.text.startswith("Alpha reported"))
    beta_claim = next(claim for claim in claims if claim.text.startswith("Beta reported"))

    assert _urls(alpha_claim) == {alpha}
    assert _urls(beta_claim) == {beta}


def test_reused_url_keeps_each_markdown_citation_instance_on_its_statement():
    shared = "https://evidence.example/shared"
    markdown = (
        "Alpha reported that revenue growth increased by 18 percent. "
        f"[Alpha filing]({shared}) "
        "Beta reported that debt risk increased after the delay. "
        f"[Beta filing]({shared})"
    )
    claims = _claims(markdown)
    alpha_claim = next(claim for claim in claims if claim.text.startswith("Alpha reported"))
    beta_claim = next(claim for claim in claims if claim.text.startswith("Beta reported"))

    assert [item.original_marker for item in alpha_claim.citations if item.url] == ["[Alpha filing]"]
    assert [item.original_marker for item in beta_claim.citations if item.url] == ["[Beta filing]"]


def test_balanced_parentheses_angle_reference_urls_and_terminal_punctuation():
    balanced = "https://evidence.example/report_(final)?view=full&year=2026"
    referenced = "https://evidence.example/archive_(audited)?download=1"
    markdown = "\n".join(
        [
            f"The market review reported revenue growth increased by 22 percent [audit]({balanced}).",
            "The risk review reported supplier debt risk increased materially [risk-ref].",
            f"[risk-ref]: <{referenced}>.",
        ]
    )

    claims = _claims(markdown)
    market_claim = next(claim for claim in claims if "market review" in claim.text)
    risk_claim = next(claim for claim in claims if "risk review" in claim.text)

    assert _urls(market_claim) == {balanced}
    assert _urls(risk_claim) == {referenced}
    assert not any(claim.text.startswith("[risk-ref]") for claim in claims)


def test_all_consecutive_corroborating_links_are_retained():
    urls = [f"https://evidence.example/corroboration/{index}" for index in range(1, 7)]
    markdown = "\n".join(
        ["The independent reviews reported that revenue growth increased by 29 percent."]
        + [f"[Independent source {index}]({url})" for index, url in enumerate(urls, 1)]
    )

    claim = next(claim for claim in _claims(markdown) if "independent reviews" in claim.text)
    assert _urls(claim) == set(urls)


def test_url_less_structured_citation_and_section_local_provenance_are_preserved():
    payload = {
        "title": "Section-local provenance",
        "sections": [
            {
                "title": "Regulatory review",
                "citations": [
                    {
                        "id": "board-minutes-7",
                        "title": "Confidential board minutes, item 7",
                        "quote": "The board reported that approval risk remains material.",
                    }
                ],
                "claims": [
                    {
                        "id": "approval-risk",
                        "text": "The board reported that approval risk remains material.",
                        "citations": ["board-minutes-7"],
                    }
                ],
            }
        ],
    }

    document = ResearchIngestionService().ingest_inline_documents([payload])[0]
    citation = document.imported_citations[0]
    claim = ExtractionService().extract_claims([document])[0]

    assert citation.url is None
    assert citation.original_source_id == "board-minutes-7"
    assert citation.section == "Regulatory review"
    assert claim.original_claim_id == "approval-risk"
    assert any(item.original_source_id == "board-minutes-7" for item in claim.citations)


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {
                "text": "A sufficiently long structured report body for validation.",
                "citations": [
                    {"id": "duplicate", "title": "First source"},
                    {"id": "duplicate", "title": "Second source"},
                ],
            },
            "Duplicate .*source ID",
        ),
        (
            {
                "claims": [
                    {"id": "duplicate", "text": "First claim reported revenue growth increased."},
                    {"id": "duplicate", "text": "Second claim reported debt risk increased."},
                ]
            },
            "Duplicate structured claim ID",
        ),
    ],
)
def test_duplicate_structured_source_and_claim_ids_are_rejected(payload, message):
    with pytest.raises(ValueError, match=message):
        ResearchIngestionService().ingest_inline_documents([payload])


def test_duplicate_markdown_reference_source_ids_are_rejected():
    markdown = "\n".join(
        [
            "The review reported revenue growth increased [source].",
            "[source]: https://evidence.example/first",
            "[SOURCE]: https://evidence.example/second",
        ]
    )
    with pytest.raises(ValueError, match="Duplicate Markdown citation source ID"):
        ResearchIngestionService().ingest_inline_documents(
            [{"filename": "duplicate-references.md", "text": markdown}]
        )


def test_duplicate_unstructured_claims_merge_sources_but_distinct_structured_ids_survive():
    statement = "The benchmark reported that revenue growth increased by 31 percent."
    service = ResearchIngestionService(chunk_size=10_000, chunk_overlap=0)
    documents = service.ingest_inline_documents(
        [
            {
                "filename": "first.md",
                "text": f"{statement}\n[First benchmark](https://evidence.example/first)",
            },
            {
                "filename": "second.md",
                "text": f"{statement}\n[Second benchmark](https://evidence.example/second)",
            },
        ]
    )
    merged = [claim for claim in ExtractionService().extract_claims(documents) if claim.text == statement]
    assert len(merged) == 1
    assert _urls(merged[0]) == {
        "https://evidence.example/first",
        "https://evidence.example/second",
    }

    structured = service.ingest_inline_documents(
        [
            {
                "claims": [
                    {
                        "id": "claim-one",
                        "text": statement,
                        "citations": [
                            {"id": "source-one", "url": "https://evidence.example/one"}
                        ],
                    },
                    {
                        "id": "claim-two",
                        "text": statement,
                        "citations": [
                            {"id": "source-two", "url": "https://evidence.example/two"}
                        ],
                    },
                ]
            }
        ]
    )
    distinct = ExtractionService().extract_claims(structured)
    assert [claim.original_claim_id for claim in distinct] == ["claim-one", "claim-two"]
    assert _urls(distinct[0]) == {"https://evidence.example/one"}
    assert _urls(distinct[1]) == {"https://evidence.example/two"}


def test_claim_inventory_is_not_silently_capped_at_160():
    markdown = " ".join(
        f"Company{index} reported revenue growth increased by {index} basis points."
        for index in range(170)
    )
    assert len(_claims(markdown)) == 170


def test_mixed_paths_reject_unsupported_or_empty_members(tmp_path):
    valid = tmp_path / "valid.md"
    valid.write_text("The review reported revenue growth increased materially.", encoding="utf-8")
    unsupported = tmp_path / "unsupported.csv"
    unsupported.write_text("not,accepted", encoding="utf-8")
    empty = tmp_path / "empty.md"
    empty.write_bytes(b"")

    service = ResearchIngestionService()
    with pytest.raises(ValueError, match="Unsupported research-pack format"):
        service.ingest_paths([valid, unsupported])
    with pytest.raises(ValueError, match="file is empty"):
        service.ingest_paths([valid, empty])


@pytest.mark.parametrize(
    "second, expected",
    [
        (FileStorage(stream=io.BytesIO(b"x"), filename="bad.csv"), "Unsupported"),
        (FileStorage(stream=io.BytesIO(b""), filename="empty.md"), "empty"),
    ],
)
def test_all_uploads_are_validated_before_any_file_is_saved(tmp_path, monkeypatch, second, expected):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "runs")
    run_id = V2Storage.create_run_id()
    first = FileStorage(
        stream=io.BytesIO(b"The review reported revenue growth increased."),
        filename="valid.md",
    )

    with pytest.raises(ValueError, match=expected):
        ResearchIngestionService().ingest_uploads(run_id, [first, second])
    assert not (V2Storage.RUNS_DIR / run_id).exists()


def test_saved_upload_is_private_and_metadata_does_not_leak_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "runs")
    run_id = V2Storage.create_run_id()
    upload = FileStorage(
        stream=io.BytesIO(b"The review reported revenue growth increased."),
        filename="private.md",
    )

    document = ResearchIngestionService().ingest_uploads(run_id, [upload])[0]
    saved = V2Storage.RUNS_DIR / run_id / "research_pack" / "private.md"

    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert document.metadata["source_filename"] == "private.md"
    assert "path" not in document.metadata


def test_url_safety_rejects_credentials_and_excessive_length_but_keeps_query():
    service = ResearchIngestionService()
    with pytest.raises(ValueError, match="embedded credentials"):
        service.ingest_inline_documents(
            [
                {
                    "text": "The review reported revenue growth increased.",
                    "citations": ["https://user:password@evidence.example/source"],
                }
            ]
        )
    with pytest.raises(ValueError, match="4096-character"):
        service.ingest_inline_documents(
            [
                {
                    "text": "The review reported revenue growth increased.",
                    "citations": ["https://evidence.example/" + "a" * 4096],
                }
            ]
        )

    url = "https://evidence.example/source?report=annual&year=2026#finding-4"
    document = service.ingest_inline_documents(
        [
            {
                "text": "The review reported revenue growth increased.",
                "citations": [url],
            }
        ]
    )[0]
    assert document.imported_citations[0].url == url


def test_url_identity_preserves_case_sensitive_path_query_and_fragment():
    upper = "https://Evidence.Example/Reports/Q1?View=Full#Finding"
    lower = "https://evidence.example/reports/q1?view=full#finding"
    document = ResearchIngestionService().ingest_inline_documents(
        [
            {
                "text": "The review documented a material comparison between two independent sources.",
                "citations": [
                    {"label": "Source", "url": upper},
                    {"label": "Source", "url": lower},
                ],
            }
        ]
    )[0]

    assert [citation.url for citation in document.imported_citations] == [upper, lower]
    assert len({citation.source_id for citation in document.imported_citations}) == 2


def test_short_positive_and_negative_declarative_evidence_are_both_retained():
    claims = _claims(
        "Alpha Cloud improved reliability and reduced operational loss. "
        "Beta Cloud increased migration risk and caused severe delay."
    )

    assert [claim.text for claim in claims] == [
        "Alpha Cloud improved reliability and reduced operational loss.",
        "Beta Cloud increased migration risk and caused severe delay.",
    ]


def test_url_less_imported_source_is_not_mislabeled_as_a_report_anchor():
    document = ResearchIngestionService().ingest_inline_documents(
        [
            {
                "title": "Structured evidence",
                "claims": [
                    {
                        "id": "claim-1",
                        "text": "The internal benchmark documented 18 percent growth.",
                        "citations": ["source-1"],
                    }
                ],
                "citations": [
                    {
                        "id": "source-1",
                        "title": "Internal benchmark",
                        "quote": "Growth was 18 percent.",
                    }
                ],
            }
        ]
    )[0]
    claims = ExtractionService().extract_claims([document])
    state = V2RunState(
        run_id="v2_20260716010101_abcdef12",
        project_name="URL-less source label",
        question="Should we proceed?",
        documents=[document],
        claims=claims,
    )

    markdown = ForecastReportService().generate(state).markdown

    assert "[preserved source without URL: Internal benchmark]" in markdown
    assert "**Preserved cited source without a URL:** Internal benchmark." in markdown
    assert "[report anchor: Internal benchmark]" not in markdown


def test_structured_claim_id_reference_does_not_attach_same_url_sibling_source():
    shared_url = "https://evidence.example/report"
    document = ResearchIngestionService().ingest_inline_documents(
        [
            {
                "claims": [
                    {
                        "id": "C1",
                        "text": "The benchmark documented 18 percent growth.",
                        "citations": [{"id": "S1"}],
                    }
                ],
                "citations": [
                    {"id": "S1", "url": shared_url, "quote": "Quote one"},
                    {"id": "S2", "url": shared_url, "quote": "Quote two"},
                ],
            }
        ]
    )[0]

    claim = ExtractionService().extract_claims([document])[0]
    external = [citation for citation in claim.citations if citation.source_type == "external_source"]

    assert [(citation.original_source_id, citation.quote) for citation in external] == [
        ("S1", "Quote one")
    ]


def test_immediately_following_bare_url_binds_to_preceding_statement_only():
    source = "https://evidence.example/source"
    claims = _claims(
        "Alpha Cloud reliability improved substantially during the evaluated production pilot.\n"
        f"{source}\n"
        "Beta Cloud migration risk remains unresolved pending a later internal review."
    )
    alpha = next(claim for claim in claims if claim.text.startswith("Alpha Cloud"))
    beta = next(claim for claim in claims if claim.text.startswith("Beta Cloud"))

    assert _urls(alpha) == {source}
    assert _urls(beta) == set()


def test_consecutive_bare_urls_all_bind_to_the_preceding_statement():
    one = "https://evidence.example/source-one"
    two = "https://evidence.example/source-two"
    claims = _claims(
        "Alpha Cloud reliability improved substantially during the evaluated production pilot.\n"
        f"{one}\n"
        f"{two}\n"
        "Beta Cloud migration risk remains unresolved pending a later internal review."
    )
    alpha = next(claim for claim in claims if claim.text.startswith("Alpha Cloud"))
    beta = next(claim for claim in claims if claim.text.startswith("Beta Cloud"))

    assert _urls(alpha) == {one, two}
    assert _urls(beta) == set()


def test_short_entity_quote_does_not_support_every_matching_claim():
    vague = "https://evidence.example/vague"
    specific = "https://evidence.example/reliability"
    reliability = "Alpha Cloud reliability improved substantially during the production pilot."
    migration = "Alpha Cloud migration risk increased materially during the production pilot."
    document = ResearchIngestionService(chunk_size=100_000, chunk_overlap=0).ingest_inline_documents(
        [
            {
                "filename": "report.md",
                "text": f"{reliability}\n{migration}",
                "citations": [
                    {"id": "S1", "url": vague, "quote": "Alpha Cloud"},
                    {"id": "S2", "url": specific, "quote": reliability},
                ],
            }
        ]
    )[0]
    claims = ExtractionService().extract_claims([document])
    reliability_claim = next(claim for claim in claims if "reliability" in claim.text)
    migration_claim = next(claim for claim in claims if "migration" in claim.text)

    assert _urls(reliability_claim) == {specific}
    assert _urls(migration_claim) == set()


def test_terminal_citation_label_is_not_treated_as_option_claim_text():
    source = "https://evidence.example/alpha-risk"
    claim = next(
        item
        for item in _claims(
            f"Beta Cloud completed setup in five days [Alpha Cloud risk data]({source})."
        )
        if item.text.startswith("Beta Cloud")
    )

    assert claim.text == "Beta Cloud completed setup in five days."
    assert _urls(claim) == {source}


def test_terminal_grammatical_object_link_remains_part_of_claim_text():
    source = "https://evidence.example/alpha-cloud"
    claim = next(
        item
        for item in _claims(
            f"The migration team ultimately selected [Alpha Cloud]({source})."
        )
        if item.text.startswith("The migration team")
    )

    assert claim.text == "The migration team ultimately selected Alpha Cloud."
    assert _urls(claim) == {source}


def test_bound_reference_markers_do_not_become_metrics_or_duplicate_claims():
    one = "https://evidence.example/one"
    two = "https://evidence.example/two"
    markdown = (
        "Alpha Cloud reported revenue growth improved strongly during the pilot.[1]\n"
        "Alpha Cloud reported revenue growth improved strongly during the pilot.[2]\n\n"
        f"[1]: {one}\n"
        f"[2]: {two}"
    )
    claims = _claims(markdown)

    assert len(claims) == 1
    assert claims[0].text == "Alpha Cloud reported revenue growth improved strongly during the pilot."
    assert _urls(claims[0]) == {one, two}
    assert DecisionIntelligenceService()._detect_contradictions(claims) == []


def test_label_only_structured_citation_attaches_to_its_claim():
    label = "Confidential benchmark appendix"
    document = ResearchIngestionService().ingest_inline_documents(
        [
            {
                "claims": [
                    {
                        "id": "C1",
                        "text": "The appendix documented a material operating benchmark.",
                        "citations": [{"label": label}],
                    }
                ]
            }
        ]
    )[0]
    claim = ExtractionService().extract_claims([document])[0]
    external = [citation for citation in claim.citations if citation.source_type == "external_source"]

    assert [(citation.label, citation.url) for citation in external] == [(label, None)]
    assert claim.provenance_status == "external_citation_preserved"


def test_repeated_identical_statement_merges_each_occurrence_citation():
    one = "https://evidence.example/one"
    two = "https://evidence.example/two"
    statement = "Alpha Cloud reported reliability improved materially during the production pilot."
    claims = _claims(
        f"{statement}\n[Source one]({one})\n"
        f"{statement}\n[Source two]({two})"
    )

    assert len(claims) == 1
    assert claims[0].text == statement
    assert _urls(claims[0]) == {one, two}
