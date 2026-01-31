import requests
from typing import Optional, Dict, Any


BASE_URL = "http://localhost/CMServiceAPI/Record"


def search_records(
    *,
    type: Optional[str] = None,
    title: Optional[str] = None,
    number: Optional[str] = None,
    created: Optional[str] = None,
    status: Optional[str] = None,
    properties: str = "NameString",
    response_format: str = "json",
) -> Dict[str, Any]:
    """
    Call CMServiceAPI Record search using native query fields.
    """

    params = {
        "format": response_format,
        "Properties": properties,
    }

    query_parts = []

    if type:
        query_parts.append(f"type:{type}")

    if title:
        query_parts.append(f"title:{title}")

    if number:
        query_parts.append(f"number:{number}")

    if created:
        query_parts.append(f"created:{created}")

    if status:
        query_parts.append(f"status:{status}")

    if query_parts:
        params["q"] = "/".join(query_parts)

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=10,
    )

    response.raise_for_status()
    return response.json()
