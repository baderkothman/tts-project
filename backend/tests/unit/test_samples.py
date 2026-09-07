"""Every difficult-content sample's expected transformation actually holds
(SC-003, FR-038a)."""

import pytest

from backend.app.data.samples import SAMPLES
from backend.app.text_processing.pipeline import process_text


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_sample_expected_transformation(sample):
    result = process_text(sample.text, locale=sample.locale)
    for expected in sample.expected_contains:
        assert expected in result.processed, (
            f"{sample.id}: expected '{expected}' in processed text, got: {result.processed}"
        )
    for forbidden in sample.expected_absent:
        assert forbidden not in result.processed, (
            f"{sample.id}: '{forbidden}' should not remain, got: {result.processed}"
        )
