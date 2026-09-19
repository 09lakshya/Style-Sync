from app.modules.ai.service import cosine_similarity
from app.modules.shopping.service import (
    DUPLICATE_THRESHOLD,
    MAX_METADATA_SCORE,
    MAX_REPORTED_SIMILARITY,
    REVIEW_THRESHOLD,
    VISUAL_DUPLICATE_GATE,
    decide_outcome,
    matching_attributes,
    score_match,
)


def test_cosine_similarity_behaviour():
    """cosine_similarity itself: identical, close and opposed vectors."""
    v1 = [0.7071, 0.7071, 0.0]
    assert cosine_similarity(v1, v1) > 0.99

    v2 = [0.7071, 0.6, 0.37]
    assert cosine_similarity(v1, v2) > 0.85

    v3 = [-0.7071, -0.7071, 0.0]
    assert cosine_similarity(v1, v3) < 0.0


def test_metadata_alone_cannot_reach_duplicate_threshold():
    """A visually unrelated item with identical colour/type/pattern must not be a duplicate.

    This is the regression guard for the previous scoring formula, under which full
    metadata agreement scored 0.86 and tripped `similar_found` with zero visual support.
    """
    score = score_match(visual_cosine=0.0, metadata_score=MAX_METADATA_SCORE)
    assert score < DUPLICATE_THRESHOLD
    assert decide_outcome(score, 0.0) == "no_strong_duplicate"


def test_metadata_match_with_moderate_visual_is_review_not_duplicate():
    """Same metadata plus middling visual agreement warrants a look, not a duplicate call."""
    score = score_match(visual_cosine=0.88, metadata_score=MAX_METADATA_SCORE)
    assert score >= REVIEW_THRESHOLD
    # Visual agreement is below the gate, so it must not be reported as a duplicate.
    assert decide_outcome(score, 0.88) == "review_matches"


def test_identical_image_is_reported_as_duplicate():
    score = score_match(visual_cosine=1.0, metadata_score=MAX_METADATA_SCORE)
    assert score == MAX_REPORTED_SIMILARITY
    assert decide_outcome(score, 1.0) == "similar_found"


def test_never_reports_absolute_certainty():
    assert score_match(1.0, MAX_METADATA_SCORE) <= MAX_REPORTED_SIMILARITY < 1.0


def test_visual_signal_outweighs_metadata_signal():
    """Strong visual agreement alone must outrank metadata agreement alone."""
    visual_only = score_match(visual_cosine=0.95, metadata_score=0.0)
    metadata_only = score_match(visual_cosine=0.0, metadata_score=MAX_METADATA_SCORE)
    assert visual_only > metadata_only


def test_negative_cosine_is_floored():
    """Opposed embeddings carry no meaning for image-image comparison."""
    assert score_match(-0.9, 0.0) == 0.0
    assert score_match(-0.9, MAX_METADATA_SCORE) == score_match(0.0, MAX_METADATA_SCORE)


def test_duplicate_gate_is_the_deciding_factor_at_equal_score():
    """Two matches with the same combined score differ only by visual agreement."""
    score = DUPLICATE_THRESHOLD + 0.01
    assert decide_outcome(score, VISUAL_DUPLICATE_GATE) == "similar_found"
    assert decide_outcome(score, VISUAL_DUPLICATE_GATE - 0.01) == "review_matches"


def test_ranking_prefers_the_visually_closer_item():
    """Ordering used by the frontend to pick the item shown in DuplicateAlertModal."""
    close_visual = score_match(visual_cosine=0.97, metadata_score=0.0)
    far_visual_same_metadata = score_match(visual_cosine=0.50, metadata_score=MAX_METADATA_SCORE)
    assert close_visual > far_visual_same_metadata


def test_metadata_match_ignores_case_of_edited_labels():
    # Hand-edited wardrobe metadata ("White", "Solid") must still match model labels.
    item = {"primary_color": "White", "type": "Blouse ", "pattern": "Solid"}
    query = {"primary_color": "white", "type": "blouse", "pattern": "striped"}
    assert matching_attributes(item, query) == ["color", "type"]


def test_missing_metadata_never_counts_as_a_match():
    assert matching_attributes({}, {"primary_color": "", "type": None, "pattern": ""}) == []
