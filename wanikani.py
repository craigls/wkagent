from typing import Generator
import requests
import os
import sys

WANIKANI_BASE_URL = "https://api.wanikani.com/v2/"
WANIKANI_MIN_SRS_STAGE = 5  # Guru
WANIKANI_SRS_STAGES = 9

session = requests.Session()


def get_user(*args, **kwargs) -> dict:
    url = WANIKANI_BASE_URL + "user"
    response = _make_request(
        "GET",
        url,
        *args,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()["data"]


def get_subjects(
    subject_type="kanji_vocabulary", level=None, cumulative=True, max_pages=sys.maxsize
) -> Generator[tuple[int, dict], None, None]:
    params = {"subject_type": subject_type}
    if level and cumulative:
        params["levels"] = ",".join([str(x) for x in range(1, level + 1)])
    elif level:
        params["levels"] = level

    return (
        (object["id"], object["data"])
        for page in _paginated_api_request(
            "GET", "subjects", max_pages=max_pages, params=params
        )
        for object in page["data"]
    )


def get_assignments(
    subject_type="kanji_vocabulary",
    level=None,
    cumulative=True,
    srs_stage=WANIKANI_MIN_SRS_STAGE,
    max_pages=sys.maxsize,
) -> Generator[tuple[int, dict], None, None]:
    params = {
        "subject_type": subject_type,
        "srs_stages": ",".join(
            [str(x) for x in range(srs_stage, WANIKANI_SRS_STAGES + 1)]
        ),
    }
    if level and cumulative:
        params["levels"] = ",".join([str(x) for x in range(1, level + 1)])
    elif level:
        params["levels"] = level

    return (
        (object["id"], object["data"])
        for page in _paginated_api_request(
            "GET", "assignments", max_pages=max_pages, params=params
        )
        for object in page["data"]
    )


def _paginated_api_request(
    method: str, endpoint: str, max_pages: int = sys.maxsize, *args, **kwargs
) -> Generator[dict, None, None]:
    url = WANIKANI_BASE_URL + endpoint
    page_count = 1
    while url and page_count <= max_pages:
        response = _make_request(
            method,
            url,
            *args,
            **kwargs,
        )
        response.raise_for_status()
        json_data = response.json()
        yield json_data
        url = json_data.get("pages", {}).get("next_url")
        page_count += 1


def _make_request(*args, **kwargs) -> requests.Response:
    session.headers.update({"Authorization": f"Bearer {os.environ['WANIKANI_TOKEN']}"})
    return session.request(
        *args,
        **kwargs,
    )
