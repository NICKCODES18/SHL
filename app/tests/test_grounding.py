"""Grounding validator tests."""

from app.agents.grounding import GroundingValidator
from app.models.schemas import AssessmentMetadata, AssessmentRecommendation


def test_rejects_unknown_url() -> None:
    catalog = {
        "Verify GAT": AssessmentMetadata(
            name="Verify GAT",
            url="https://www.shl.com/products/product-catalog/view/verify-gat/",
            test_type="Cognitive",
            cognitive=True,
        )
    }
    validator = GroundingValidator(catalog)
    recs = validator.validate_and_fix(
        [
            AssessmentRecommendation(
                name="Fake Test",
                url="https://evil.com/fake",
                test_type="X",
            )
        ]
    )
    assert recs == []


def test_accepts_catalog_match() -> None:
    url = "https://www.shl.com/products/product-catalog/view/verify-gat/"
    catalog = {
        "Verify GAT": AssessmentMetadata(
            name="Verify GAT", url=url, test_type="Cognitive"
        )
    }
    validator = GroundingValidator(catalog)
    recs = validator.validate_and_fix(
        [AssessmentRecommendation(name="Verify GAT", url=url, test_type="Cognitive")]
    )
    assert len(recs) == 1
    assert recs[0].url == url
