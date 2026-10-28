"""Load candidate profiles without assigning behavioral score targets."""

from pathlib import Path

from .schema import LearnerProfile, require
from .storage import read_json

DATA = Path(__file__).parent / "data"


def load_profiles() -> dict[str, LearnerProfile]:
    profiles = [LearnerProfile.parse(item) for item in read_json(DATA / "profiles.json")]
    require(len({p.profile_id for p in profiles}) == len(profiles), "Duplicate profile IDs")
    return {p.profile_id: p for p in profiles}
