"""The season head is withheld: predict_axes and single_label must not report it."""

import pytest

from app.modules.ai.classifier_manager import classifier_manager

AXES = {
    "occasion": {"labels": ["casual", "formal", "party"], "multi_label": True},
    "season": {"labels": ["summer", "winter"], "multi_label": True},
    "tradition": {"labels": ["ethnic"], "multi_label": False, "negative_label": "western"},
}
THRESHOLDS = {"casual": 0.47, "formal": 0.85, "party": 0.97, "summer": 0.57, "winter": 0.65, "ethnic": 0.59}


@pytest.fixture
def probabilities(monkeypatch):
    def _set(scores: dict[str, float]):
        monkeypatch.setattr(type(classifier_manager), "is_loaded", property(lambda self: True))
        monkeypatch.setattr(classifier_manager, "axes", AXES)
        monkeypatch.setattr(classifier_manager, "thresholds", THRESHOLDS)
        monkeypatch.setattr(classifier_manager, "_probabilities", lambda image: scores)

    return _set


def test_predict_axes_leaves_season_out_but_keeps_its_probabilities(probabilities):
    # What the served head gives a puffer jacket.
    probabilities({"casual": 0.95, "formal": 0.2, "party": 0.01, "summer": 0.99, "winter": 0.04, "ethnic": 0.0})
    axes = classifier_manager.predict_axes(None)

    assert "season" not in axes
    assert axes["occasion"] == ["casual"]
    assert axes["tradition"] == "western"
    assert axes["probabilities"]["summer"] == 0.99


def test_single_label_never_falls_back_to_season(probabilities):
    # A plain white tee: no occasion clears its cut, summer is at 1.0.
    probabilities({"casual": 0.43, "formal": 0.8, "party": 0.28, "summer": 1.0, "winter": 0.04, "ethnic": 0.32})
    label, confidence = classifier_manager.single_label(classifier_manager._probabilities(None))

    assert label is None
    # The near miss is the closest reported label, not summer.
    assert confidence == 0.43
