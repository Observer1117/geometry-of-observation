#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry"

def load(name):
    return json.loads((REG / name).read_text(encoding="utf-8"))

index = load("research_index.json")
wp = load("wordpress_data_model.json")
mapping = load("jsonld_mapping.json")
jsonld = load("research_index.jsonld")

assert index["schema"] == {"name":"observer-research-index","version":"1.0.0"}
assert index["registry"]["scope"] == "cross-repository"
assert index["authority"]["display_name"] == "Stassis Stashkevichyus"
assert index["authority"]["orcid"] == "https://orcid.org/0009-0000-2294-705X"
assert index["project"]["name"] == "The Observer of Multiverses"
assert index["project"]["author_entity"] is False

works = index["works"]
assert len(works) == 5
assert index["index_page"]["number_of_items"] == 5
assert sorted(w["priority"] for w in works) == [1,2,3,4,5]
assert len({w["id"] for w in works}) == 5
assert len({w["slug"] for w in works}) == 5
assert len({w["site_path"] for w in works}) == 5
allowed_primary = {"ScholarlyArticle","Dataset"}
allowed_release = {"public-research-corpus","metadata-successor-of-frozen-preprint","preprint","release-candidate"}
allowed_review = {"not-peer-reviewed","independent-specialist-review-pending"}
for w in works:
    assert w["site_path"] == f'/research/{w["slug"]}/'
    assert w["release_status"] in allowed_release
    assert w["review_status"] in allowed_review
    assert w["license_scope"]
    assert w["jsonld_profile"]["primary_type"] in allowed_primary
    assert len(w["source_contract"]["merge_commit"]) == 40
    if w["id"] == "QMD-2.0-rc2":
        assert w["doi"] is None and w["github_release_url"] is None
        assert w["review_status"] == "independent-specialist-review-pending"
        assert w["novelty_gate"] == "G2-not-passed"
        assert w["independent_verification_gate"] == "G6-not-passed"
    if w["id"] == "CRSE-0.2":
        assert w["metadata_record_version"] == "0.2.1"
        assert w["citation_version"] == "0.2"
        assert w["doi_scope"] == "frozen-version-0.2"

assert wp["schema"] == {"name":"observer-wordpress-data-model","version":"1.0.0"}
cpt = wp["custom_post_type"]
assert cpt["key"] == "research_output" and len(cpt["key"]) <= 20
assert cpt["show_in_rest"] is True and cpt["rest_base"] == "research"
assert "custom-fields" in cpt["supports"]
assert wp["rest_contract"]["meta_show_in_rest"] is True
assert wp["rest_contract"]["requires_custom_fields_support"] is True
meta_keys = {x["key"] for x in wp["machine_meta"]}
for key in {"observer_work_id","observer_metadata_record_version","observer_citation_version","observer_release_status","observer_review_status","observer_repository_url","observer_display_date","observer_license_scope","observer_schema_primary_type","observer_source_repository","observer_source_contract_path","observer_source_commit"}:
    assert key in meta_keys

assert mapping["schema"]["context"] == "https://schema.org"
assert mapping["research_index"]["page_type"] == "CollectionPage"
assert mapping["research_index"]["main_entity_type"] == "ItemList"
assert mapping["global_entities"]["person"]["type"] == "Person"
assert mapping["global_entities"]["website"]["type"] == "WebSite"

assert jsonld["@context"] == "https://schema.org"
graph = jsonld["@graph"]
types = [n.get("@type") for n in graph]
for t in ["Person","WebSite","CollectionPage","ItemList"]:
    assert t in types
itemlist = next(n for n in graph if n.get("@type") == "ItemList")
assert itemlist["numberOfItems"] == 5
assert [x["position"] for x in itemlist["itemListElement"]] == [1,2,3,4,5]
assert len({x["item"]["@id"] for x in itemlist["itemListElement"]}) == 5
print("Research Index / WordPress / JSON-LD registry contract verified.")
