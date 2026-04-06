import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import requests

BOOKMAKERS = ["racenetstandard"]
BET_TYPES = ["fixed-win", "fixed-place"]
PRICE_TYPE = ["bookmaker", "best"]


class QueryType(Enum):
    MEETINGS_DATE = 0
    MEETINGS_DATE_COUNTRY = 1
    MEETINGS_TIME = 2
    MEETING_SLUG = 3
    FULL_FORM = 4
    STATS = 5
    EVENT = 6
    ODDS = 7
    SECTIONAL = 8
    PREDICTOR_SETTINGS = 9


class Variables:
    _type: QueryType

    def get_dict(self):
        return {}


@dataclass
class MeetingsDateQueryVariables(Variables):
    startDate: str
    endDate: str
    _type: QueryType = QueryType.MEETINGS_DATE

    def get_dict(self):
        return {"startDate": self.startDate, "endDate": self.endDate}


@dataclass
class MeetingsDateCountryQueryVariables(Variables):
    startDate: str
    endDate: str
    country: str
    _type: QueryType = QueryType.MEETINGS_DATE_COUNTRY

    def get_dict(self):
        return {
            "startDate": self.startDate,
            "endDate": self.endDate,
            "country": self.country,
        }


@dataclass
class MeetingsTimeQueryVariables(Variables):
    startTime: str
    endTime: str
    limit: int
    sports_id: int = 1
    _type: QueryType = QueryType.MEETINGS_TIME

    def get_dict(self):
        return {
            "startTime": self.startTime,
            "endTime": self.endTime,
            "limit": self.limit,
            "sportIds": self.sports_id,
        }


@dataclass
class MeetingSlugQueryVariables(Variables):
    slug: str
    _type: QueryType = QueryType.MEETING_SLUG

    def get_dict(self):
        return {"slug": self.slug}


@dataclass
class FullFormQueryVariables(Variables):
    selectionIds: list[str]
    limit: int
    _type: QueryType = QueryType.FULL_FORM

    def get_dict(self):
        return {"selectionIds": self.selectionIds, "limit": self.limit}


@dataclass
class SectionalQueryVariables(Variables):
    selectionIds: list[str]
    _type: QueryType = QueryType.SECTIONAL

    def get_dict(self):
        return {
            "selectionIds": self.selectionIds,
        }


@dataclass
class StatsQueryVariables(Variables):
    eventId: str
    _type: QueryType = QueryType.STATS

    def get_dict(self):
        return {"eventId": self.eventId}


@dataclass
class EventQueryVariables(Variables):
    eventId: str
    _type: QueryType = QueryType.EVENT

    def get_dict(self):
        return {"eventId": self.eventId}


@dataclass
class OddsQueryVariables(Variables):
    eventId: str
    bookmakers: list[str] = field(default_factory=lambda: BOOKMAKERS)
    betTypes: list[str] = field(default_factory=lambda: BET_TYPES)
    priceType: list[str] = field(default_factory=list)
    fluctuations: int = 4
    _type: QueryType = QueryType.ODDS


@dataclass
class PredictorSettingsQueryVariables(Variables):
    brand: str = "punters"
    _type: QueryType = QueryType.PREDICTOR_SETTINGS

    def get_dict(self):
        return {}


OPERATION_NAMES = {
    QueryType.MEETINGS_DATE: "meetingsByStartEndDate",
    QueryType.MEETINGS_DATE_COUNTRY: "meetingsByStartEndDateAndCountryName",
    QueryType.MEETINGS_TIME: "meetingsIndexByStartEndTime",
    QueryType.MEETING_SLUG: "meetingBySlug",
    QueryType.FULL_FORM: "fullFormsBySelectionIds",
    QueryType.STATS: "statsByEventId",
    QueryType.EVENT: "eventById",
    QueryType.SECTIONAL: "getSectionalsBySelectionIds",
    QueryType.PREDICTOR_SETTINGS: "predictorSettingsDefaults",
}

QUERY_HASHES_FILE = Path(__file__).with_name("query_hashes.json")

DEFAULT_QUERY_HASHES = {
    QueryType.MEETINGS_DATE: "223af3d0cbfa0a25e744c34941835eca3a91e6dbc8f121128fa2acd7361c2062",
    QueryType.MEETINGS_DATE_COUNTRY: "7e3f50657b051fdfd5059245f55682fba76f14c6898e6f9de3b7653205195f0c",
    QueryType.MEETINGS_TIME: "80eb89d41ec583cd84078e2ee7eaa572bcdaae0432ee70c4fda1eb8bda246e8d",
    QueryType.MEETING_SLUG: "e353a397746c38cbbc7efdf98495314692e10654532d8cc26fe0aeae7aa97058",
    QueryType.FULL_FORM: "ed7986a7b3dfaafe2e3801a9b04e7941c2e5291ef97d2cb6d2de2a1b9c6662f1",
    QueryType.STATS: "5e6e59dd2725d40f214cc3d4680b9934660f9fd1b89c2d8111b22d30f8c03dc6",
    QueryType.EVENT: "8fff49d83321193fce3b3a0c39bdcff4c74dc0725feede61b6b726c84d76845d",
    QueryType.SECTIONAL: "05aba715ad18f10f5b526c18f109cd37dbbc7f20655d6b6822941e9b9086ae00",
    QueryType.PREDICTOR_SETTINGS: "b3c0e6a5157e60028513deb46b643cfcc464fda6cc10bc58ebcce6c21d4f4c0c",
}


def load_query_hashes() -> dict[QueryType, str]:
    query_hashes = DEFAULT_QUERY_HASHES.copy()

    try:
        with QUERY_HASHES_FILE.open("r", encoding="utf-8") as hash_file:
            file_hashes = json.load(hash_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return query_hashes

    if not isinstance(file_hashes, dict):
        return query_hashes

    for query_type_name, query_hash in file_hashes.items():
        if not isinstance(query_type_name, str) or not isinstance(query_hash, str):
            continue
        try:
            query_type = QueryType[query_type_name]
        except KeyError:
            continue
        if query_hash:
            query_hashes[query_type] = query_hash

    return query_hashes


QUERY_HASHES = load_query_hashes()


@dataclass
class QueryInfo:
    query_type: QueryType
    variables: Variables

    def get_query_params(self):
        if self.variables._type != self.query_type:
            raise ValueError("Variables type does not match operation type")
        if self.query_type == QueryType.ODDS:
            if not isinstance(self.variables, OddsQueryVariables):
                raise ValueError("Variables type does not match operation type")
            params = {
                "bookmaker": ",".join(self.variables.bookmakers),
                "betTypes": ",".join(self.variables.betTypes),
                "priceFluctuations": str(self.variables.fluctuations),
            }
            if len(self.variables.priceType) > 0:
                params["type"] = ",".join(self.variables.priceType)
        else:
            params = {
                "operationName": self.get_operation_name(),
                "variables": json.dumps(self.variables.get_dict()),
                "extensions": json.dumps(
                    {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": self.get_query_hash(),
                        }
                    }
                ),
            }
        return params

    def get_query_hash(self):
        return QUERY_HASHES[self.query_type]

    def get_operation_name(self):
        return OPERATION_NAMES[self.query_type]


HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ja;q=0.7",
    "authorization": "Bearer none",
    "content-type": "application/json",
    "if-none-match": 'W/"5b688-ToRJqLdEWaZOc815FCqVIVZ6klM"',
    "origin": "https://www.racenet.com.au",
    "priority": "u=1, i",
    "referer": "https://www.racenet.com.au/",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


class QueryRequest:
    MAX_RETRIES = 5

    def __init__(self, query_info: QueryInfo):
        self.query_info = query_info
        self.retry = 0

    def send_request(self) -> dict:
        if self.query_info.query_type == QueryType.ODDS:
            if not isinstance(self.query_info.variables, OddsQueryVariables):
                raise ValueError("Variables type does not match operation type")

            request_url = (
                f"https://puntapi.com/odds/au/event/{self.query_info.variables.eventId}"
            )
        else:
            request_url = "https://puntapi.com/graphql-horse-racing"

        response = requests.get(
            request_url, headers=HEADERS, params=self.query_info.get_query_params()
        )
        if response.status_code != 200:
            return self.retry_request()
        try:
            response_json = response.json()
            if response_json.get("errors") is not None:
                return {}
            if self.query_info.query_type == QueryType.ODDS:
                response_data = response_json.get("odds")
            else:
                response_data = response_json.get("data")
            if response_data is not None:
                if len(response_data) == 0:
                    return {}
            else:
                return {}
            return response_json
        except json.decoder.JSONDecodeError:
            return self.retry_request()

    def retry_request(self) -> dict:
        self.retry += 1
        if self.retry >= self.MAX_RETRIES:
            print("Request failed after 5 retries")
            return {}
        print(f"Request: {self.query_info} failed. Retrying in 1 sec...")
        time.sleep(2)
        return self.send_request()
