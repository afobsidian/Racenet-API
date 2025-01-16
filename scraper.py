from datetime import datetime, timedelta
from api_queries import QueryInfo, QueryRequest, QueryType, FullFormQueryVariables, \
    StatsQueryVariables, EventQueryVariables, MeetingsTimeQueryVariables, \
    OddsQueryVariables, MeetingSlugQueryVariables, SectionalQueryVariables, \
    MeetingsDateQueryVariables

from meetings_data import Meeting, Jockey, Trainer, Event, Selection, Prediction
from typing import Optional
import multiprocessing


class MeetingsScraper:

    def create_meetings_time_query(self, scrape_date: datetime) -> QueryRequest:
        scrape_date -= timedelta(days=1)
        start_of_day = scrape_date.replace(
            hour=13, minute=0, second=0, microsecond=0)
        start_time = start_of_day.strftime(
            "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        tomorrow = scrape_date + timedelta(days=1)
        end_of_day = tomorrow.replace(
            hour=12, minute=59, second=59, microsecond=999)
        end_time = end_of_day.strftime(
            "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        meetings_variables = MeetingsTimeQueryVariables(
            startTime=start_time, endTime=end_time, limit=100)
        meetings_query = QueryInfo(
            query_type=QueryType.MEETINGS_TIME,
            variables=meetings_variables)
        return QueryRequest(query_info=meetings_query)

    def create_meetings_date_query(self, scrape_date: datetime) -> QueryRequest:
        start_date = scrape_date.strftime("%Y-%m-%d")
        end_date = scrape_date.strftime("%Y-%m-%d")
        meetings_variables = MeetingsDateQueryVariables(
            startDate=start_date, endDate=end_date)
        meetings_query = QueryInfo(
            query_type=QueryType.MEETINGS_DATE,
            variables=meetings_variables)
        return QueryRequest(query_info=meetings_query)

    def create_meeting_query(self, slug: str) -> QueryRequest:
        meeting_variables = MeetingSlugQueryVariables(slug=slug)
        meeting_query = QueryInfo(
            query_type=QueryType.MEETING_SLUG,
            variables=meeting_variables)
        return QueryRequest(query_info=meeting_query)

    def create_event_query(self, event_id: str) -> QueryRequest:
        event_variables = EventQueryVariables(eventId=event_id)
        event_query = QueryInfo(
            query_type=QueryType.EVENT,
            variables=event_variables)
        return QueryRequest(query_info=event_query)

    def create_stats_query(self, event_id: str) -> QueryRequest:
        stats_variables = StatsQueryVariables(eventId=event_id)
        stats_query = QueryInfo(
            query_type=QueryType.STATS,
            variables=stats_variables)
        return QueryRequest(query_info=stats_query)

    def create_odds_query(self, event_id: str) -> QueryRequest:
        odds_variables = OddsQueryVariables(eventId=event_id)
        odds_query = QueryInfo(
            query_type=QueryType.ODDS,
            variables=odds_variables)
        return QueryRequest(query_info=odds_query)

    def create_form_query(self, selection_ids: list) -> QueryRequest:
        form_query = QueryInfo(
            query_type=QueryType.FULL_FORM,
            variables=FullFormQueryVariables(
                selectionIds=selection_ids, limit=10))
        return QueryRequest(query_info=form_query)

    def create_sectional_query(self, selection_ids: list) -> QueryRequest:
        sectional_query = QueryInfo(
            query_type=QueryType.SECTIONAL,
            variables=SectionalQueryVariables(selectionIds=selection_ids))
        return QueryRequest(query_info=sectional_query)

    def parse_meetings_response_time(self, response: dict) -> list[str]:
        meetings_data = response.get('data')
        if meetings_data is None:
            return []
        meetings_groups = meetings_data.get('meetingsGrouped')
        if meetings_groups is None:
            return []
        australia_meetings = []
        for meeting_group in meetings_groups:
            if meeting_group.get('group') == "Australia":
                australia_meetings = meeting_group.get('meetings')
                break

        meeting_slugs = []
        for meeting in australia_meetings:
            meeting_slugs.append(meeting['slug'])
        return meeting_slugs

    def parse_meetings_response_date(self, response: dict) -> list[str]:
        meetings_data = response.get('data')
        if meetings_data is None:
            return []
        meetings_groups = meetings_data.get('meetings')
        if meetings_groups is None:
            return []
        australia_meetings = []
        for meeting in meetings_groups:
            venue_data = meeting.get('venue')
            if venue_data is not None:
                country_data = venue_data.get('country')
                if country_data is not None:
                    if country_data.get('name') == "Australia":
                        australia_meetings.append(meeting)

        meeting_slugs = []
        for meeting in australia_meetings:
            meeting_slugs.append(meeting['slug'])
        return meeting_slugs

    def parse_meeting_response(self, response: dict) -> Optional[Meeting]:
        response_data = response.get('data')
        if response_data is None:
            return None

        meeting_data = response_data.get('meeting')
        if meeting_data is None:
            return None
        meeting = Meeting.from_dict(meeting_data)
        meeting.events.sort(key=lambda x: x.event_number)
        delete_events = []
        for index, event in enumerate(meeting.events):
            event_query = self.create_event_query(str(event.event_id))
            event_response = event_query.send_request()
            event_response_data = event_response.get('data')
            if event_response_data is None:
                continue
            event_data = event_response_data.get('event')
            if event_data is None:
                continue
            meeting.events[index] = Event.from_dict(event_data)
            # if multiple selections numbers are none, continue
            if all(
                    selection.number is None
                    for selection in meeting.events[index].selections):
                delete_events.append(index)
                continue
            meeting.events[index].selections.sort(
                key=lambda x: x.number)

            stats_query = self.create_stats_query(str(event.event_id))
            stats_response = stats_query.send_request()
            stats_response_data = stats_response.get('data')
            if stats_response_data is None:
                continue
            stats_data = stats_response_data.get('stats')
            if stats_data is None:
                continue
            for selection in meeting.events[index].selections:
                for stats in stats_data:
                    if selection.id == stats.get('selectionId'):
                        selection.add_stats(stats)

            odds_query = self.create_odds_query(str(event.event_id))
            odds_response = odds_query.send_request()
            odds_response_data = odds_response.get('odds')
            if odds_response_data is None:
                continue
            for selection in meeting.events[index].selections:
                for odds_response in odds_response_data:
                    if selection.id == str(odds_response.get('selectionId', 0)):
                        selection.add_odds(odds_response)

            selection_ids = []
            for selection in meeting.events[index].selections:
                if selection.id != "":
                    selection_ids.append(selection.id)
            form_query = self.create_form_query(selection_ids)
            form_response = form_query.send_request()
            form_response_data = form_response.get('data')
            if form_response_data is None:
                continue

            forms_data = form_response_data.get('competitorForms')
            if forms_data is None:
                continue
            for form in forms_data:
                for selection in meeting.events[index].selections:
                    if selection.id == form.get('selectionId'):
                        selection.add_runs(form.get('forms', []))
                        selection.runs.sort(
                            key=lambda x: datetime.strptime(x.meeting_date, "%Y-%m-%d"), reverse=True)

            selection_ids = []
            for selection in meeting.events[index].selections:
                if selection.id != "":
                    selection_ids.append(selection.id)
            sectional_query = self.create_sectional_query(selection_ids)
            sectional_response = sectional_query.send_request()
            sectional_response_data = sectional_response.get('data')
            if sectional_response_data is None:
                continue

            sectionals_data = sectional_response_data.get('competitorForms')
            if sectionals_data is None:
                continue
            for sectional in sectionals_data:
                for selection in meeting.events[index].selections:
                    if selection.id == sectional.get('selectionId'):
                        selection.add_sectional_splits(
                            sectional.get('forms', []))

        for index in reversed(delete_events):
            del meeting.events[index]
        if len(meeting.events) == 0:
            return None
        return meeting

    def get_meetings(
            self, scrape_date: datetime = datetime.now(),
            time_query: bool = False) -> list[Meeting]:
        if time_query:
            meetings_request = self.create_meetings_time_query(scrape_date)
            meetings_response = meetings_request.send_request()
            meetings_slugs = self.parse_meetings_response_time(
                meetings_response)
        else:
            meetings_request = self.create_meetings_date_query(scrape_date)
            meetings_response = meetings_request.send_request()
            meetings_slugs = self.parse_meetings_response_date(
                meetings_response)
        with multiprocessing.Pool() as pool:
            meetings_list = pool.map(self.get_meeting, meetings_slugs)
        formatted_meeting_list: list[Meeting] = [
            meeting for meeting in meetings_list if meeting is not None]
        return formatted_meeting_list

    def get_meeting(self, slug: str) -> Optional[Meeting]:
        meeting_request = self.create_meeting_query(slug)
        meeting_response = meeting_request.send_request()
        return self.parse_meeting_response(meeting_response)
