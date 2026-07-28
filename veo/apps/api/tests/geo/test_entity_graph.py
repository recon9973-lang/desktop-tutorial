"""The entity graph: what ``@id`` links to what, not whether a script tag exists.

``lxml`` and ``beautifulsoup4`` are not installed in this environment, so the parser
underneath is the standard library. These tests cover the awkward shapes real sites emit
— ``@graph`` arrays, bare objects, nested references, and JSON that does not parse.
"""

from __future__ import annotations

from tests.geo.support import load_case

from veo.geo.entity_graph import build_entity_graph
from veo.geo.parsing import parse_html

GRAPH = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","@id":"https://a.example/#org","name":"가나다","url":"https://a.example/",
  "logo":"https://a.example/logo.png","sameAs":["https://x.example/a","https://y.example/a"]},
 {"@type":"WebPage","@id":"https://a.example/p#page","about":{"@id":"https://a.example/#org"}}
]}
</script></head><body></body></html>
"""

NO_IDS = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"가나다"}
</script></head><body></body></html>
"""

BROKEN = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"가나다",,}
</script></head><body></body></html>
"""

ORPHAN = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","@id":"https://a.example/#org","name":"가나다","url":"https://a.example/"},
 {"@type":"WebPage","@id":"https://a.example/p#page","name":"페이지"}
]}
</script></head><body></body></html>
"""


def graph_of(html: str):
    return build_entity_graph(parse_html(html))


def test_a_page_with_no_json_ld_reports_no_structured_data() -> None:
    graph = graph_of("<html><body><p>안녕하세요</p></body></html>")
    assert not graph.has_structured_data
    assert graph.nodes == ()


def test_a_graph_array_is_flattened_into_nodes() -> None:
    graph = graph_of(GRAPH)
    assert graph.has_structured_data
    assert {node.node_id for node in graph.nodes} == {
        "https://a.example/#org",
        "https://a.example/p#page",
    }


def test_a_bare_object_is_a_single_node() -> None:
    graph = graph_of(NO_IDS)
    assert len(graph.nodes) == 1
    assert graph.nodes[0].name == "가나다"


def test_the_organization_node_is_found_by_type() -> None:
    organization = graph_of(GRAPH).primary_organization()
    assert organization is not None
    assert organization.name == "가나다"
    assert organization.url == "https://a.example/"
    assert organization.logo
    assert len(organization.same_as) == 2


def test_references_between_nodes_are_resolved() -> None:
    graph = graph_of(GRAPH)
    coherence = graph.coherence()
    assert coherence.nodes_with_ids == 2
    assert "https://a.example/#org" in coherence.referenced_ids
    assert coherence.orphan_ids == ()


def test_a_node_nobody_points_at_is_an_orphan() -> None:
    coherence = graph_of(ORPHAN).coherence()
    assert coherence.orphan_ids


def test_missing_ids_are_reported_without_an_exception() -> None:
    coherence = graph_of(NO_IDS).coherence()
    assert coherence.nodes_with_ids == 0


def test_unparseable_json_ld_is_recorded_not_raised() -> None:
    graph = graph_of(BROKEN)
    assert graph.parse_errors
    assert graph.has_structured_data


def test_address_and_telephone_are_lifted_from_a_nested_postal_address() -> None:
    organization = graph_of(
        """
        <html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Dentist","name":"온담치과의원",
         "telephone":"02-555-0130",
         "address":{"@type":"PostalAddress","streetAddress":"서초대로 122 3층",
                    "addressLocality":"서울특별시 서초구"}}
        </script></head><body></body></html>
        """
    ).primary_organization()
    assert organization is not None
    assert organization.telephone == "02-555-0130"
    assert "서초대로 122" in organization.address_text
    assert "서울특별시 서초구" in organization.address_text


def test_the_hospital_fixture_produces_a_coherent_graph() -> None:
    document = load_case("hospital_local").context.primary_document
    assert document is not None
    graph = build_entity_graph(parse_html(document.text()))
    coherence = graph.coherence()

    assert graph.has_structured_data
    assert not graph.parse_errors
    assert coherence.orphan_ids == ()
    assert coherence.nodes_with_ids == len(graph.nodes)

    organization = graph.primary_organization()
    assert organization is not None
    assert organization.name == "온담치과의원"
    assert organization.same_as


def test_the_generic_fixture_has_structured_data_but_no_identifiers() -> None:
    document = load_case("generic_service").context.primary_document
    assert document is not None
    graph = build_entity_graph(parse_html(document.text()))
    assert graph.has_structured_data
    assert graph.parse_errors
    assert graph.coherence().nodes_with_ids == 0
