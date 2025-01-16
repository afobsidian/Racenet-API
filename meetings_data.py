from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime, timezone
from statistics import stdev

SPELL_THRESHOLD = 90
FRESHEST_THRESHOLD = 30


@dataclass
class OddsFluctuation:
    price: float
    rolling_mean_deviation: float
    time: str

    @classmethod
    def from_dict(cls, data: dict) -> 'OddsFluctuation':
        if data is None:
            return cls(
                price=0.0,
                rolling_mean_deviation=0.0,
                time=""
            )

        time_data = data.get('updatedAt')
        if time_data is None:
            return cls(
                price=data.get('value', 0.0),
                rolling_mean_deviation=data.get('rollingMeanDeviation', 0.0),
                time=""
            )

        # 2024-12-20T07:00:00.000Z convert to 24 hour sydney time with MS precision
        utc_time = datetime.strptime(time_data, "%Y-%m-%dT%H:%M:%S.%fZ")
        sydney_time = utc_time.replace(
            tzinfo=timezone.utc).astimezone(tz=None)
        time = sydney_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        return cls(
            price=data.get('value', 0.0),
            rolling_mean_deviation=data.get('rollingMeanDeviation', 0.0),
            time=time
        )


@dataclass
class Odds:
    bookmaker: Literal["racenetstandard", "bet365", "betfair"]
    bet_type: Literal["Win", "Place"]
    price: float
    movement: float
    market_percentage: float
    fluctuations: list[OddsFluctuation]

    @classmethod
    def from_dict(cls, data: dict) -> 'Odds':
        if data is None:
            return cls(
                bookmaker="",
                bet_type="",
                price=0.0,
                movement=0.0,
                market_percentage=0.0,
                fluctuations=[]
            )
        bet_type = data.get('betType', "")
        if bet_type == "fixed-place":
            bet_type = "Place"
        else:
            bet_type = "Win"

        bookmaker = data.get('bookmakerId', "")
        if bookmaker == "bet365":
            bookmaker = "bet365"
        elif bookmaker == "racenetstandard":
            bookmaker = "racenetstandard"
        else:
            bookmaker = "betfair"

        price_data = data.get('price', {})
        if price_data is None:
            return cls(
                bookmaker=bookmaker,
                bet_type=bet_type,
                price=0.0,
                movement=0.0,
                market_percentage=data.get('marketPercentage', 0.0),
                fluctuations=[]
            )

        price_value = price_data.get('value', 0.0)
        movement = price_data.get('movement', 0.0)

        fluctuation_data = price_data.get('fluctuations', [])
        fluctuations = []
        for fluctuation in fluctuation_data:
            fluctuations.append(OddsFluctuation.from_dict(fluctuation))

        return cls(
            bookmaker=bookmaker, bet_type=bet_type, price=price_value,
            movement=movement, market_percentage=data.get(
                'marketPercentage', 0.0),
            fluctuations=fluctuations)


@dataclass
class Prediction:
    normalized_speed: float
    normalized_speed_position: str
    model_output: float
    model_rank: int
    winning_chance: float
    speed: float
    finish_speed: float

    @classmethod
    def from_dict(cls, data: dict) -> 'Prediction':
        if data is None:
            return cls(
                normalized_speed=0.0,
                normalized_speed_position="",
                model_output=0.0,
                model_rank=0,
                winning_chance=0.0,
                speed=0.0,
                finish_speed=0.0,
            )
        normalized_speed = data.get('normSpeedMeasure', 0.0)
        if normalized_speed == None:
            normalized_speed = 0.0
        return cls(
            normalized_speed=float(normalized_speed),
            normalized_speed_position=data.get(
                'normSpeedMeasureRatingName', ""),
            model_output=data.get('modelOutput', 0.0),
            model_rank=data.get('modelRank', 0),
            winning_chance=data.get('winningChance', 0.0),
            speed=data.get('speedMeasure', 0.0),
            finish_speed=data.get('finishSpeed', 0.0)
        )


@dataclass
class Jockey:
    id: int
    name: str
    last_year_runs: int
    last_year_win_percentage: float
    last_year_place_percentage: float

    @classmethod
    def from_dict(cls, data: dict) -> 'Jockey':
        if data is None:
            return cls(
                id=0,
                name="",
                last_year_runs=0,
                last_year_win_percentage=0.0,
                last_year_place_percentage=0.0
            )

        stats = data.get('stats', {})
        if stats is None:
            return cls(
                id=data.get('id', 0),
                name=data.get('name', ""),
                last_year_runs=0,
                last_year_win_percentage=0.0,
                last_year_place_percentage=0.0
            )

        last_year_places_list = stats.get('lastYearPlaces', [])
        if len(last_year_places_list) < 3:
            last_year_runs = 0
            last_year_win_percentage = 0.0
            last_year_place_percentage = 0.0
        else:
            last_year_wins = last_year_places_list[0]
            last_year_places = last_year_places_list[1]
            last_year_places += last_year_places_list[2]
            last_year_runs = stats.get('lastYearRuns')
            if last_year_runs == 0 or last_year_runs is None:
                last_year_win_percentage = 0.0
                last_year_place_percentage = 0.0
                last_year_runs = 0
            else:
                last_year_win_percentage = float(
                    last_year_wins / last_year_runs)
                last_year_place_percentage = float(
                    last_year_places / last_year_runs)
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ""),
            last_year_runs=last_year_runs,
            last_year_win_percentage=last_year_win_percentage,
            last_year_place_percentage=last_year_place_percentage
        )


@dataclass
class Trainer:
    id: int
    name: str
    location: str
    last_year_runs: int
    last_year_win_percentage: float
    last_year_place_percentage: float

    @classmethod
    def from_dict(cls, data: dict) -> 'Trainer':
        if data is None:
            return cls(
                id=0,
                name="",
                location="",
                last_year_runs=0,
                last_year_win_percentage=0.0,
                last_year_place_percentage=0.0
            )
        stats = data.get('stats', {})
        if stats is None:
            return cls(
                id=data.get('id', 0),
                name=data.get('name', ""),
                location=data.get('location', ""),
                last_year_runs=0,
                last_year_win_percentage=0.0,
                last_year_place_percentage=0.0
            )

        last_year_places_list = stats.get('lastYearPlaces', [])
        if len(last_year_places_list) < 3:
            last_year_runs = 0
            last_year_win_percentage = 0.0
            last_year_place_percentage = 0.0
        else:
            last_year_wins = last_year_places_list[0]
            last_year_places = last_year_places_list[1]
            last_year_places += last_year_places_list[2]
            last_year_runs = stats.get('lastYearRuns')
            if last_year_runs == 0 or last_year_runs is None:
                last_year_win_percentage = 0.0
                last_year_place_percentage = 0.0
                last_year_runs = 0
            else:
                last_year_win_percentage = float(
                    last_year_wins / last_year_runs)
                last_year_place_percentage = float(
                    last_year_places / last_year_runs)
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ""),
            location=data.get('location', ""),
            last_year_runs=last_year_runs,
            last_year_win_percentage=last_year_win_percentage,
            last_year_place_percentage=last_year_place_percentage
        )


@dataclass
class FormBenchmark:
    runner_tempo_quantile_rank: Optional[float]
    runner_tempo_label: str
    runner_tempo_difference: Optional[float]
    leader_tempo_label: str
    leader_tempo_difference: Optional[float]
    runner_time_difference: Optional[float]
    winner_time_label: str
    winner_time_difference: Optional[float]
    runner_time_difference_l800: Optional[float]
    runner_time_difference_l600: Optional[float]
    runner_time_difference_l400: Optional[float]
    runner_time_difference_l200: Optional[float]
    runner_race_position_l800: int
    runner_race_position_l600: int
    runner_race_position_l400: int
    runner_race_position_l200: int
    runner_meeting_position_l800: int
    runner_meeting_position_l600: int
    runner_meeting_position_l400: int
    runner_meeting_position_l200: int

    @classmethod
    def from_dict(cls, data: dict) -> 'FormBenchmark':
        if data is None:
            return cls(
                runner_tempo_quantile_rank=None,
                runner_tempo_label="",
                runner_tempo_difference=None,
                leader_tempo_label="",
                leader_tempo_difference=None,
                runner_time_difference=None,
                winner_time_label="",
                winner_time_difference=None,
                runner_time_difference_l800=None,
                runner_time_difference_l600=None,
                runner_time_difference_l400=None,
                runner_time_difference_l200=None,
                runner_race_position_l800=0,
                runner_race_position_l600=0,
                runner_race_position_l400=0,
                runner_race_position_l200=0,
                runner_meeting_position_l800=0,
                runner_meeting_position_l600=0,
                runner_meeting_position_l400=0,
                runner_meeting_position_l200=0
            )
        runner_tempo_quantile_rank_data = data.get('runnerTempoQuantileRank')
        if runner_tempo_quantile_rank_data == None:
            runner_tempo_quantile_rank = None
        elif type(runner_tempo_quantile_rank_data) == str:
            runner_tempo_quantile_rank = float(runner_tempo_quantile_rank_data)

        runner_tempo_difference_data = data.get('runnerTempoDifference')
        if runner_tempo_difference_data == None:
            runner_tempo_difference = None
        elif type(runner_tempo_difference_data) == str:
            runner_tempo_difference = float(runner_tempo_difference_data)

        leader_tempo_difference_data = data.get('leaderTempoDifference')
        if leader_tempo_difference_data == None:
            leader_tempo_difference = None
        elif type(leader_tempo_difference_data) == str:
            leader_tempo_difference = float(leader_tempo_difference_data)

        runner_time_difference_data = data.get('runnerTimeDifference')
        if runner_time_difference_data == None:
            runner_time_difference = None
        elif type(runner_time_difference_data) == str:
            runner_time_difference = float(runner_time_difference_data)

        winner_time_difference_data = data.get('winnerTimeDifference')
        if winner_time_difference_data == None:
            winner_time_difference = None
        elif type(winner_time_difference_data) == str:
            winner_time_difference = float(winner_time_difference_data)

        runner_time_difference_l800_data = data.get('runnerTimeDifferenceL800')
        if runner_time_difference_l800_data == None:
            runner_time_difference_l800 = None
        elif type(runner_time_difference_l800_data) == str:
            runner_time_difference_l800 = float(
                runner_time_difference_l800_data)

        runner_time_difference_l600_data = data.get('runnerTimeDifferenceL600')
        if runner_time_difference_l600_data == None:
            runner_time_difference_l600 = None
        elif type(runner_time_difference_l600_data) == str:
            runner_time_difference_l600 = float(
                runner_time_difference_l600_data)

        runner_time_difference_l400_data = data.get('runnerTimeDifferenceL400')
        if runner_time_difference_l400_data == None:
            runner_time_difference_l400 = None
        elif type(runner_time_difference_l400_data) == str:
            runner_time_difference_l400 = float(
                runner_time_difference_l400_data)

        runner_time_difference_l200_data = data.get('runnerTimeDifferenceL200')
        if runner_time_difference_l200_data == None:
            runner_time_difference_l200 = None
        elif type(runner_time_difference_l200_data) == str:
            runner_time_difference_l200 = float(
                runner_time_difference_l200_data)

        runner_race_position_l800_data = data.get('runnerRacePositionL800')
        if runner_race_position_l800_data == None:
            runner_race_position_l800 = 0
        elif type(runner_race_position_l800_data) == str:
            runner_race_position_l800 = int(runner_race_position_l800_data)

        runner_race_position_l600_data = data.get('runnerRacePositionL600')
        if runner_race_position_l600_data == None:
            runner_race_position_l600 = 0
        elif type(runner_race_position_l600_data) == str:
            runner_race_position_l600 = int(runner_race_position_l600_data)

        runner_race_position_l400_data = data.get('runnerRacePositionL400')
        if runner_race_position_l400_data == None:
            runner_race_position_l400 = 0
        elif type(runner_race_position_l400_data) == str:
            runner_race_position_l400 = int(runner_race_position_l400_data)

        runner_race_position_l200_data = data.get('runnerRacePositionL200')
        if runner_race_position_l200_data == None:
            runner_race_position_l200 = 0
        elif type(runner_race_position_l200_data) == str:
            runner_race_position_l200 = int(runner_race_position_l200_data)

        runner_meeting_position_l800_data = data.get(
            'runnerMeetingPositionL800')
        if runner_meeting_position_l800_data == None:
            runner_meeting_position_l800 = 0
        elif type(runner_meeting_position_l800_data) == str:
            runner_meeting_position_l800 = int(
                runner_meeting_position_l800_data)

        runner_meeting_position_l600_data = data.get(
            'runnerMeetingPositionL600')
        if runner_meeting_position_l600_data == None:
            runner_meeting_position_l600 = 0
        elif type(runner_meeting_position_l600_data) == str:
            runner_meeting_position_l600 = int(
                runner_meeting_position_l600_data)

        runner_meeting_position_l400_data = data.get(
            'runnerMeetingPositionL400')
        if runner_meeting_position_l400_data == None:
            runner_meeting_position_l400 = 0
        elif type(runner_meeting_position_l400_data) == str:
            runner_meeting_position_l400 = int(
                runner_meeting_position_l400_data)

        runner_meeting_position_l200_data = data.get(
            'runnerMeetingPositionL200')
        if runner_meeting_position_l200_data == None:
            runner_meeting_position_l200 = 0
        elif type(runner_meeting_position_l200_data) == str:
            runner_meeting_position_l200 = int(
                runner_meeting_position_l200_data)

        return cls(
            runner_tempo_quantile_rank=runner_tempo_quantile_rank,
            runner_tempo_label=data.get('runnerTempoLabel', ""),
            runner_tempo_difference=runner_tempo_difference,
            leader_tempo_label=data.get('leaderTempoLabel', ""),
            leader_tempo_difference=leader_tempo_difference,
            runner_time_difference=runner_time_difference,
            winner_time_label=data.get('winnerTimeLabel', ""),
            winner_time_difference=winner_time_difference,
            runner_time_difference_l800=runner_time_difference_l800,
            runner_time_difference_l600=runner_time_difference_l600,
            runner_time_difference_l400=runner_time_difference_l400,
            runner_time_difference_l200=runner_time_difference_l200,
            runner_race_position_l800=runner_race_position_l800,
            runner_race_position_l600=runner_race_position_l600,
            runner_race_position_l400=runner_race_position_l400,
            runner_race_position_l200=runner_race_position_l200,
            runner_meeting_position_l800=runner_meeting_position_l800,
            runner_meeting_position_l600=runner_meeting_position_l600,
            runner_meeting_position_l400=runner_meeting_position_l400,
            runner_meeting_position_l200=runner_meeting_position_l200
        )


@dataclass
class Splits:
    runner_split_l800: float
    runner_split_l600: float
    runner_split_l400: float
    runner_split_l200: float
    runner_split_finish: float

    @classmethod
    def from_dict(cls, data: dict) -> 'Splits':
        if data is None:
            return cls(
                runner_split_l800=0.0,
                runner_split_l600=0.0,
                runner_split_l400=0.0,
                runner_split_l200=0.0,
                runner_split_finish=0.0
            )
        sectional_times = data.get('sectionalTime', {})
        if sectional_times is None:
            return cls(
                runner_split_l800=0.0,
                runner_split_l600=0.0,
                runner_split_l400=0.0,
                runner_split_l200=0.0,
                runner_split_finish=0.0
            )

        l800_data = sectional_times.get('l800', {})
        l600_data = sectional_times.get('l600', {})
        l400_data = sectional_times.get('l400', {})
        l200_data = sectional_times.get('l200', {})
        finish_data = sectional_times.get('finish', {})
        if l800_data is None:
            l800_data = {}
        if l600_data is None:
            l600_data = {}
        if l400_data is None:
            l400_data = {}
        if l200_data is None:
            l200_data = {}
        if finish_data is None:
            finish_data = {}

        return cls(
            runner_split_l800=l800_data.get('split', 0.0),
            runner_split_l600=l600_data.get('split', 0.0),
            runner_split_l400=l400_data.get('split', 0.0),
            runner_split_l200=l200_data.get('split', 0.0),
            runner_split_finish=finish_data.get('split', 0.0)
        )


@dataclass
class PositionSummary:
    distance: int
    position: Optional[int]
    time: str

    @classmethod
    def from_dict(cls, data: dict) -> 'PositionSummary':
        if data is None:
            return cls(
                distance=0,
                position=None,
                time=""
            )
        return cls(
            distance=data.get('distance', 0),
            position=data.get('position'),
            time=data.get('time', "")
        )


@dataclass
class Run:
    id: str
    finish_position: int
    starters: int
    margin: float
    meeting_name: str
    meeting_date: str
    distance: int
    track_condition: str
    prize_money: float
    barrier: str
    weight: float
    starting_price: float
    open_price: float
    fluctuation: float
    winner_time: str
    winner_name: str
    second_name: str
    second_margin: float
    third_name: str
    third_margin: float
    video_comment: str
    video_note: str
    days_since_last: int
    competitors_won_since: int
    is_trial: bool
    is_class: bool
    jockey: Jockey
    trainer: Trainer
    venue: str
    _class: str
    benchmark_threshold: float
    l600_time: float
    finish_time: float
    position_summaries: list[PositionSummary]
    form_benchmark: FormBenchmark
    splits: Splits
    runs_since_spell: Optional[int]

    @classmethod
    def from_dict(cls, data: dict) -> 'Run':
        if data is None:
            return cls(
                id="",
                finish_position=0,
                starters=0,
                margin=0.0,
                meeting_name="",
                meeting_date="",
                distance=0,
                track_condition="",
                prize_money=0.0,
                barrier="",
                weight=0.0,
                starting_price=0.0,
                open_price=0.0,
                fluctuation=0.0,
                winner_time="",
                winner_name="",
                second_name="",
                second_margin=0.0,
                third_name="",
                third_margin=0.0,
                video_comment="",
                video_note="",
                days_since_last=0,
                competitors_won_since=0,
                is_trial=False,
                is_class=False,
                jockey=Jockey.from_dict({}),
                trainer=Trainer.from_dict({}),
                venue="",
                _class="",
                benchmark_threshold=0.0,
                l600_time=0.0,
                finish_time=0.0,
                position_summaries=[],
                form_benchmark=FormBenchmark.from_dict({}),
                splits=Splits.from_dict({}),
                runs_since_spell=None
            )

        track_condition_data = data.get('trackCondition', "")
        track_rating_data = data.get('trackConditionRating', 0)
        if track_condition_data == None or track_rating_data == None:
            track_condition = ""
        else:
            track_condition = f"{track_condition_data} {track_rating_data}"

        venue = ""
        _class = ""
        benchmark_threshold = 0.0
        competitors_won_since = 0
        selection = data.get('selection', {})
        if selection is not None:
            event = selection.get('event', {})
            if event is not None:
                _class = event.get('eventClass', "")
                benchmark_threshold = event.get('benchmarkThreshold', 0.0)
                meeting = event.get('meeting', {})
                competitors_won_since = event.get('competitorsWonSince', 0)
                if meeting is not None:
                    venue = meeting.get('name', "")
        else:
            selection = {}

        l600_time = 0.0
        finish_time = 0.0
        sectional_times = data.get('sectionalTime', {})
        if sectional_times is not None:
            l600_data = sectional_times.get('l600', {})
            if l600_data is not None:
                l600_time = l600_data.get('time', 0.0)

            finish_data = sectional_times.get('finish', {})
            if finish_data is not None:
                finish_time = finish_data.get('time', 0.0)

        position_summaries_data = []
        position_summaries: list[PositionSummary] = []
        position_summaries_data = data.get('competitorPositionSummary', [])
        for summary in position_summaries_data:
            position_summaries.append(PositionSummary.from_dict(summary))

        # if position summary doesn't have pos check sectionalTimes
        for summary in position_summaries:
            if summary.position is None:
                distance = summary.distance
                if distance not in [200, 400, 600, 800]:
                    continue
                sectional_times = data.get('sectionalTime', {})
                if sectional_times is None:
                    continue
                sectional_time_data = sectional_times.get(f'l{distance}', {})
                if sectional_time_data is None:
                    continue
                summary.position = sectional_time_data.get('position')

        if data.get('isFirstUp', False):
            runs_since_spell = 0
        elif data.get('isSecondUp', False):
            runs_since_spell = 1
        elif data.get('isThirdUp', False):
            runs_since_spell = 2
        else:
            runs_since_spell = 3  # 4th up or more

        return cls(
            id=data.get('id', ""),
            finish_position=data.get('finishPosition', 0),
            starters=data.get('eventStarters', 0),
            margin=data.get('margin', 0.0),
            meeting_name=data.get('meetingName', ""),
            meeting_date=data.get('meetingDate', ""),
            distance=data.get('eventDistance', 0),
            track_condition=track_condition, prize_money=data.get(
                'racePrizeMoney', 0.0),
            barrier=data.get('barrier', ""),
            weight=data.get('weightCarried', 0.0),
            starting_price=data.get('startingWinPriceDecimal', 0.0),
            open_price=data.get('openPrice', 0.0),
            fluctuation=data.get('fluctuation1', 0.0),
            winner_time=data.get('winnerTime', ""),
            winner_name=data.get('winnerName', ""),
            second_name=data.get('secondName', ""),
            second_margin=data.get('secondMarginDecimal', 0.0),
            third_name=data.get('thirdName', ""),
            third_margin=data.get('thirdMarginDecimal', 0.0),
            video_comment=data.get('videoComment', ""),
            video_note=data.get('videoNote', ""),
            days_since_last=data.get('daysSinceLastRun', 0),
            competitors_won_since=competitors_won_since,
            is_trial=data.get('isTrial', False),
            is_class=data.get('isClass', False),
            jockey=Jockey.from_dict(selection.get('jockey', {})),
            trainer=Trainer.from_dict(selection.get('trainer', {})),
            venue=venue, _class=_class, benchmark_threshold=benchmark_threshold,
            l600_time=l600_time, finish_time=finish_time,
            position_summaries=position_summaries,
            form_benchmark=FormBenchmark.from_dict(
                data.get('competitorFormBenchmark', {})),
            splits=Splits.from_dict({}),
            runs_since_spell=runs_since_spell
        )


@dataclass
class PreparationStats:
    first_up_win_percentage: float
    first_up_average_difference: float
    first_up_stdev_difference: float
    second_up_win_percentage: float
    second_up_average_difference: float
    second_up_stdev_difference: float
    third_up_win_percentage: float
    third_up_average_difference: float
    third_up_stdev_difference: float
    nth_up_win_percentage: float
    nth_up_average_difference: float
    nth_up_stdev_difference: float

    @classmethod
    def from_runs(cls, runs: list[Run]) -> 'PreparationStats':
        non_trial_runs: list[Run] = [
            run for run in runs if run.is_trial == False]

        first_up_runs = [
            run for run in non_trial_runs if run.runs_since_spell == 0]
        second_up_runs = [
            run for run in non_trial_runs if run.runs_since_spell == 1]
        third_up_runs = [
            run for run in non_trial_runs if run.runs_since_spell == 2]
        nth_up_runs = [
            run for run in non_trial_runs if run.runs_since_spell == 3]

        first_up_win_percentage = 0.0
        first_up_average_difference = 0.0
        first_up_stdev_difference = 0.0
        if len(first_up_runs) != 0:
            first_up_win_percentage = float(
                len([run for run in first_up_runs if run.finish_position == 1]) / len(first_up_runs))
            first_up_differences = []
            for run in first_up_runs:
                if run.form_benchmark.runner_time_difference is not None:
                    first_up_differences.append(
                        run.form_benchmark.runner_time_difference)
            if len(first_up_differences) > 0:
                first_up_average_difference = sum(first_up_differences) \
                    / len(first_up_differences)
                if len(first_up_differences) >= 2:
                    first_up_stdev_difference = stdev(first_up_differences)

        second_up_win_percentage = 0.0
        second_up_average_difference = 0.0
        second_up_stdev_difference = 0.0
        if len(second_up_runs) != 0:
            second_up_win_percentage = float(
                len([run for run in second_up_runs if run.finish_position == 1]) / len(second_up_runs))
            second_up_differences = []
            for run in second_up_runs:
                if run.form_benchmark.runner_time_difference is not None:
                    second_up_differences.append(
                        run.form_benchmark.runner_time_difference)
            if len(second_up_differences) > 0:
                second_up_average_difference = sum(second_up_differences) \
                    / len(second_up_differences)
                if len(second_up_differences) >= 2:
                    second_up_stdev_difference = stdev(
                        second_up_differences)

        third_up_win_percentage = 0.0
        third_up_average_difference = 0.0
        third_up_stdev_difference = 0.0
        if len(third_up_runs) != 0:
            third_up_win_percentage = float(
                len([run for run in third_up_runs if run.finish_position == 1]) / len(third_up_runs))
            third_up_differences = []
            for run in third_up_runs:
                if run.form_benchmark.runner_time_difference is not None:
                    third_up_differences.append(
                        run.form_benchmark.runner_time_difference)
            if len(third_up_differences) > 0:
                third_up_average_difference = sum(third_up_differences) \
                    / len(third_up_differences)
                if len(third_up_differences) >= 2:
                    third_up_stdev_difference = stdev(
                        third_up_differences)

        nth_up_win_percentage = 0.0
        nth_up_average_difference = 0.0
        nth_up_stdev_difference = 0.0
        if len(nth_up_runs) != 0:
            nth_up_win_percentage = float(
                len([run for run in nth_up_runs if run.finish_position == 1]) / len(nth_up_runs))
            nth_up_differences = []
            for run in nth_up_runs:
                if run.form_benchmark.runner_time_difference is not None:
                    nth_up_differences.append(
                        run.form_benchmark.runner_time_difference)
            if len(nth_up_differences) > 0:
                nth_up_average_difference = sum(nth_up_differences) \
                    / len(nth_up_differences)
                if len(nth_up_differences) >= 2:
                    nth_up_stdev_difference = stdev(nth_up_differences)

        return cls(
            first_up_win_percentage=first_up_win_percentage,
            first_up_average_difference=first_up_average_difference,
            first_up_stdev_difference=first_up_stdev_difference,
            second_up_win_percentage=second_up_win_percentage,
            second_up_average_difference=second_up_average_difference,
            second_up_stdev_difference=second_up_stdev_difference,
            third_up_win_percentage=third_up_win_percentage,
            third_up_average_difference=third_up_average_difference,
            third_up_stdev_difference=third_up_stdev_difference,
            nth_up_win_percentage=nth_up_win_percentage,
            nth_up_average_difference=nth_up_average_difference,
            nth_up_stdev_difference=nth_up_stdev_difference
        )

    def get_preparation_stats(self, run_since_spell: int) -> tuple[float, float, float]:
        if run_since_spell == 0:
            return self.first_up_win_percentage, self.first_up_average_difference, \
                self.first_up_stdev_difference
        elif run_since_spell == 1:
            return self.second_up_win_percentage, self.second_up_average_difference, \
                self.second_up_stdev_difference
        elif run_since_spell == 2:
            return self.third_up_win_percentage, self.third_up_average_difference, \
                self.third_up_stdev_difference
        else:
            return self.nth_up_win_percentage, self.nth_up_average_difference, \
                self.nth_up_stdev_difference


@dataclass
class Selection:
    id: str
    name: str
    slug: str
    number: int
    barrier: int
    gear_changes: str
    comments: str
    weight: float
    claim: float
    punters_edge: float
    prediction: Prediction
    jockey: Jockey
    trainer: Trainer
    external_comments: dict[str, str]
    runs: list[Run]
    days_since_last: int
    runs_since_spell: int
    trainer_jockey_win_percentage: float
    total_runs: int
    total_wins: int
    total_places: int
    average_prize_money: float
    wet_runs_win_percentage: float
    wet_runs_place_percentage: float
    roi: float
    odds: list[Odds]
    preparation_stats: PreparationStats

    @classmethod
    def from_dict(cls, data: dict) -> 'Selection':
        if data is None:
            return cls(
                id="",
                name="",
                slug="",
                number=0,
                barrier=0,
                gear_changes="",
                comments="",
                weight=0.0,
                claim=0.0,
                punters_edge=0.0,
                prediction=Prediction.from_dict({}),
                jockey=Jockey.from_dict({}),
                trainer=Trainer.from_dict({}),
                external_comments={},
                runs=[],
                days_since_last=0,
                runs_since_spell=0,
                trainer_jockey_win_percentage=0.0,
                total_runs=0,
                total_wins=0,
                total_places=0,
                average_prize_money=0.0,
                wet_runs_win_percentage=0.0,
                wet_runs_place_percentage=0.0,
                roi=0.0,
                odds=[],
                preparation_stats=PreparationStats.from_runs([])
            )

        competitor = data.get('competitor')
        if competitor is not None:
            name = competitor.get('name', "")
            slug = competitor.get('slug', "")
        else:
            name = ""
            slug = ""

        punters_edge_data = data.get('puntersEdge')
        if punters_edge_data is not None:
            punters_edge = punters_edge_data.get('rating', 0.0)
        else:
            punters_edge = 0.0

        external_comments = {}
        selection_comments = data.get('selectionComments', [])
        for comment in selection_comments:
            brand = comment.get('brand', "")
            text = comment.get('comments', "")
            external_comments[brand] = text

        weight_data = data.get('weight', 0.0)
        if type(weight_data) == str:
            weight = float(weight_data)
        else:
            weight = 0.0

        claim_data = data.get('jockeyWeightClaim', 0.0)
        if type(claim_data) == str:
            claim = float(claim_data)
        else:
            claim = 0.0

        return cls(
            id=data.get('id', ""),
            name=name,
            slug=slug,
            number=data.get('competitorNumber', 0),
            barrier=data.get('barrierNumber', 0),
            gear_changes=data.get('gearChanges', ""),
            comments=data.get('comments', ""),
            weight=weight,
            claim=claim,
            punters_edge=punters_edge,
            prediction=Prediction.from_dict(data.get('prediction', {})),
            jockey=Jockey.from_dict(data.get('jockey', {})),
            trainer=Trainer.from_dict(data.get('trainer', {})),
            external_comments=external_comments,
            runs=[],
            days_since_last=0,
            runs_since_spell=0,
            trainer_jockey_win_percentage=0.0,
            total_runs=0,
            total_wins=0,
            total_places=0,
            average_prize_money=0.0,
            wet_runs_win_percentage=0.0,
            wet_runs_place_percentage=0.0,
            roi=0.0,
            odds=[],
            preparation_stats=PreparationStats.from_runs([])
        )

    def add_runs(self, runs: list[dict]):
        for run in runs:
            self.runs.append(Run.from_dict(run))

        self.add_preparation_stats()

        non_trial_runs: list[Run] = [
            run for run in self.runs if run.is_trial == False]
        for index, non_trial_run in enumerate(non_trial_runs):
            if index == 0:
                to_date = datetime.today()
            else:
                to_date_string = non_trial_runs[index - 1].meeting_date
                to_date = datetime.strptime(to_date_string, "%Y-%m-%d")
            from_date_string = non_trial_run.meeting_date
            from_date = datetime.strptime(from_date_string, "%Y-%m-%d")
            days_since_last = (to_date - from_date).days
            if index == 0:
                self.days_since_last = days_since_last
            if days_since_last > SPELL_THRESHOLD:
                self.runs_since_spell = index
                break
            elif index == len(non_trial_runs) - 1:
                self.runs_since_spell = len(non_trial_runs)
                break

    def add_stats(self, stats: dict):
        self.trainer_jockey_win_percentage = stats.get(
            'trainerJockeyWin', 0.0)
        self.total_runs = stats.get('totalRuns', 0)
        total_places = stats.get('totalPlaces', [])
        if len(total_places) == 3:
            self.total_wins = total_places[0]
            self.total_places = total_places[1] + total_places[2]

        self.place_percentage = stats.get('placePercentage', 0.0)
        self.average_prize_money = stats.get('averagePrizeMoney', 0.0)
        wet_runs = stats.get('wetRuns', 0)
        if wet_runs != 0:
            wet_places = stats.get('wetPlaces', [])
            if len(wet_places) == 3:
                self.wet_runs_win_percentage = float(
                    wet_places[0] / wet_runs) * 100
                wet_placings = wet_places[1] + wet_places[2]
                self.wet_runs_place_percentage = float(
                    wet_placings / wet_runs) * 100

        self.roi = stats.get('roi', 0.0)

    def add_odds(self, odds: dict):
        self.odds.append(Odds.from_dict(odds))

    def add_sectional_splits(self, splits: list[dict]):
        for run in self.runs:
            for split in splits:
                if run.id == split.get('id', ""):
                    run.splits = Splits.from_dict(split)
                    break

    def add_preparation_stats(self):
        self.preparation_stats = PreparationStats.from_runs(self.runs)


@dataclass
class Event:
    event_id: int
    name: str
    slug: str
    time: str
    event_number: int
    distance: int
    starters: int
    _class: str
    prize_money: int
    pace: float
    track_condition: str
    track_type: str
    weather: str
    comments: dict[str, str]
    selections: list[Selection]

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        event_comments = data.get('comments', [])
        comments = {}
        for comment in event_comments:
            brand = comment.get('brand', "")
            text = comment.get('comments', "")
            comments[brand] = text

        selections = []
        for selection in data.get('selections', []):
            status = selection.get('status', "")
            if status == "SCRATCHED":
                continue
            selections.append(Selection.from_dict(selection))

        track_condition_data = data.get('trackCondition')
        if track_condition_data is not None:
            overall = track_condition_data.get('overall', "")
            rating = track_condition_data.get('rating', "")
            if overall == None or rating == None:
                track_condition = ""
            else:
                track_condition = f"{overall} {rating}"
            track_type = track_condition_data.get('surface', "")
        else:
            track_condition = ""
            track_type = ""

        weather_data = data.get('weather')
        if weather_data is not None:
            weather = weather_data.get('condition', "")
        else:
            weather = ""

        time_data = data.get('startTime', "")
        if time_data == None:
            time = ""
        else:
            # 2024-12-20T07:00:00.000Z convert to 12 hour sydney time
            utc_time = datetime.strptime(time_data, "%Y-%m-%dT%H:%M:%S.%fZ")
            sydney_time = utc_time.replace(
                tzinfo=timezone.utc).astimezone(tz=None)
            time = sydney_time.strftime("%I:%M %p")

        return cls(
            event_id=data.get('id', 0),
            name=data.get('name', ""),
            slug=data.get('slug', ""),
            time=time,
            event_number=data.get('eventNumber', 0),
            distance=data.get('distance', 0),
            starters=data.get('starters', 0),
            _class=data.get('eventClass', ""),
            prize_money=data.get('racePrizeMoney', 0),
            pace=data.get('pace', 0.0),
            track_condition=track_condition,
            track_type=track_type,
            weather=weather,
            comments=comments,
            selections=selections
        )


@dataclass
class Meeting:
    meeting_id: str
    name: str
    slug: str
    state: str
    rail_position: str
    events: list[Event]

    @classmethod
    def from_dict(cls, data: dict) -> 'Meeting':
        events = []
        for event in data.get('events', []):
            events.append(Event.from_dict(event))

        return cls(
            meeting_id=data.get('id', ""),
            name=data.get('name', ""),
            slug=data.get('slug', ""),
            state=data.get('state', ""),
            rail_position=data.get('railPosition', ""),
            events=events
        )


def group_by_state(meetings: list[Meeting]) -> dict[str, list[Meeting]]:
    state_groups: dict[str, list[Meeting]] = {}
    for meeting in meetings:
        state = meeting.state
        if state not in state_groups:
            state_groups[state] = []
        state_groups[state].append(meeting)
    return state_groups
