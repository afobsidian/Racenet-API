import requests
import json
from dataclasses import dataclass, field
from enum import Enum

BOOKMAKERS = ["bet365", "betfair"]
BET_TYPES = ["fixed-win", "exchange-win", "exchange-win-lay", "fixed-place"]
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


class Variables:
    _type: QueryType

    def get_dict(self):
        return {}


@dataclass
class MeetingsDateQueryVariables(Variables):
    limit: int
    startDate: str
    endDate: str
    country: str
    _type: QueryType = QueryType.MEETINGS_DATE

    def get_dict(self):
        return {
            "limit": self.limit,
            "startDate": self.startDate,
            "endDate": self.endDate,
            "venue": {"country": self.country}
        }


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
            "country": self.country
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
            "sportIds": self.sports_id
        }


@dataclass
class MeetingSlugQueryVariables(Variables):
    slug: str
    _type: QueryType = QueryType.MEETING_SLUG

    def get_dict(self):
        return {
            "slug": self.slug
        }


@dataclass
class FullFormQueryVariables(Variables):
    selectionIds: list[str]
    limit: int
    _type: QueryType = QueryType.FULL_FORM

    def get_dict(self):
        return {
            "selectionIds": self.selectionIds,
            "limit": self.limit
        }


@dataclass
class StatsQueryVariables(Variables):
    eventId: str
    _type: QueryType = QueryType.STATS

    def get_dict(self):
        return {
            "eventId": self.eventId
        }


@dataclass
class EventQueryVariables(Variables):
    eventId: str
    _type: QueryType = QueryType.EVENT

    def get_dict(self):
        return {
            "eventId": self.eventId
        }


@dataclass
class OddsQueryVariables(Variables):
    eventId: str
    bookmakers: list[str] = field(default_factory=lambda: BOOKMAKERS)
    betTypes: list[str] = field(default_factory=lambda: BET_TYPES)
    priceType: list[str] = field(default_factory=lambda: PRICE_TYPE)
    fluctuations: int = 4
    _type: QueryType = QueryType.ODDS

    def get_dict(self):
        return {
            "selectionIds": self.selectionIds
        }


OPERATION_NAMES = {
    QueryType.MEETINGS_DATE: "meetingsByStartEndDate",
    QueryType.MEETINGS_DATE_COUNTRY: "meetingsByStartEndDateAndCountryName",
    QueryType.MEETINGS_TIME: "meetingsIndexByStartEndTime",
    QueryType.MEETING_SLUG: "meetingBySlug",
    QueryType.FULL_FORM: "fullFormsBySelectionIds",
    QueryType.STATS: "statsByEventId",
    QueryType.EVENT: "eventById"
}

QUERY_HASHES = {
    QueryType.MEETINGS_DATE: "c60f0f85d96b77e70c7ce05d6ccf60229274ad0cf6e32a6b382c18b7a0dbeaa6",
    QueryType.MEETINGS_DATE_COUNTRY: "1a5b01a2238d2b290f819bbd98788d92f17b7bc39303e2058d47f44698fb1515",
    QueryType.MEETINGS_TIME: "b8b5bef7544da6d9bc3f601bf6e030a3de79ca24e168186b110692a4302bcbfb",
    QueryType.MEETING_SLUG: "6d11913e7745daf6e5c2de9a5b72d7ad5a4f1ea82ad400832a198fe20fd2b2d2",
    QueryType.FULL_FORM: "1093c7bd100804b3372236e69b6da0549161408ca5ec53d5d72d1e2bc33eaaf1",
    QueryType.STATS: "388a5fa2d209f3f5a9c78c5cee87d5a4f9cbc1942c25a7f12f67036d79ab2a73",
    QueryType.EVENT: "0029451798d3780a964eef179e79ddad1f1074c93038774ec8626b8b22999e6d"
}


@dataclass
class QueryInfo:
    query_type: QueryType
    variables: Variables

    def get_query_params(self):
        if self.variables._type != self.query_type:
            raise ValueError("Variables type does not match operation type")
        if self.query_type == QueryType.ODDS:
            if type(self.variables) != OddsQueryVariables:
                raise ValueError("Variables type does not match operation type")
            params = {
                "bookmaker": ",".join(self.variables.bookmakers),
                "betTypes": ",".join(self.variables.betTypes),
                "type": ",".join(self.variables.priceType),
                "priceFluctuations": str(self.variables.fluctuations),
            }
        else:
            params = {
                "operationName": self.get_operation_name(),
                "variables": json.dumps(self.variables.get_dict()),
                "extensions": json.dumps({
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": self.get_query_hash()
                    }
                })
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
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


class QueryRequest:
    def __init__(self, query_info: QueryInfo):
        self.query_info = query_info

    def send_request(self) -> dict:
        if self.query_info.query_type == QueryType.ODDS:
            if type(self.query_info.variables) != OddsQueryVariables:
                raise ValueError("Variables type does not match operation type")

            request_url = f"https://puntapi.com/odds/au/event/{self.query_info.variables.eventId}"
        else:
            request_url = "https://puntapi.com/graphql-horse-racing"

        response = requests.get(
            request_url,
            headers=HEADERS,
            params=self.query_info.get_query_params()
        )
        if response.status_code != 200:
            print(response)
            print("Request failed")
            exit(1)

        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            print(response)
            raise ValueError("Invalid JSON response")
