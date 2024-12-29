from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from meetings_data import Meeting, group_by_state, Event, Selection, Run, PositionSummary, \
    FormBenchmark, Trainer, Jockey, Prediction, Odds, OddsFluctuation, Splits, SPELL_THRESHOLD, \
    PreparationStats
from scraper import MeetingsScraper
from datetime import datetime
import qdarkstyle
import sys
from typing import Union, Optional
from numerize import numerize
from difflib import SequenceMatcher
from textwrap import shorten

SCREEN_SIZE = QtCore.QSize()
FONT = "Helvetica"


def screen_width_percentage(percentage: float) -> int:
    return int(SCREEN_SIZE.width() * percentage)


def screen_height_percentage(percentage: float) -> int:
    return int(SCREEN_SIZE.height() * percentage)


class EventTickTimer(QtCore.QTimer):
    def __init__(self, event: Event):
        super(EventTickTimer, self).__init__()
        self.event_time = datetime.strptime(event.time, "%I:%M %p")


class TitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(TitleLabel, self).__init__(text)
        self.setFont(QtGui.QFont(FONT, 26, weight=QtGui.QFont.Weight.Bold))
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class SubtitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(SubtitleLabel, self).__init__(text)
        self.setFont(QtGui.QFont(FONT, 16, weight=QtGui.QFont.Weight.Bold))
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class HeadingLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(HeadingLabel, self).__init__(text)
        self.setFont(QtGui.QFont(FONT, 10, weight=QtGui.QFont.Weight.Bold))
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)


class InfoLabel(QtWidgets.QLabel):
    def __init__(self, data: Union[str, int, float, object], font_size: int):
        if type(data) is float:
            text = f"{data:.2f}"
        elif type(data) is int:
            text = f"{data:,}"
        elif type(data) is str:
            text = data
        else:
            text = str(data)
        super(InfoLabel, self).__init__(text)
        self.setFont(QtGui.QFont(FONT, font_size))
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("background-color: transparent;")


class LargeInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(LargeInfoLabel, self).__init__(data, 14)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class SmallInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(SmallInfoLabel, self).__init__(data, 10)


class VerySmallInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(VerySmallInfoLabel, self).__init__(data, 8)


class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # round the corners
        self.setStyleSheet("background-color: #c0c0c0;")


class QVLine(QtWidgets.QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.setFixedWidth(1)
        # round the corners
        self.setStyleSheet("background-color: #c0c0c0;")


class HorizontalBar(QtWidgets.QFrame):
    def __init__(self, value: float, max_value: float):
        super(HorizontalBar, self).__init__()

        self.value = value
        self.max_value = max_value * 1.05
        self.setFixedHeight(screen_height_percentage(0.02))
        self.setFixedWidth(screen_width_percentage(0.092))
        value = int((self.value / self.max_value) * self.width())
        self.setFixedWidth(value)
        self.setStyleSheet(
            f"background-color: #00FF00; border-radius: 5;")


class TempoWidget(QtWidgets.QWidget):
    def __init__(self, benchmark: Optional[float], label: str):
        super(TempoWidget, self).__init__()
        self.benchmark = benchmark
        self.tempo_label = label
        self.displaying_benchmark = True

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if benchmark is not None:
            label_text = f"{benchmark:.2f}"
        else:
            label_text = " - "
        self.label = SmallInfoLabel(label_text)
        if label is not None:
            if "fast" in label.lower():
                self.label.setStyleSheet("color: lightgreen;")
            elif "slow" in label.lower():
                self.label.setStyleSheet("color: red;")

        layout.addWidget(self.label)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and \
                event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.displaying_benchmark:
                if self.tempo_label is None or self.tempo_label == "":
                    self.label.setText(" -- ")
                else:
                    self.label.setText(self.tempo_label)
                self.displaying_benchmark = False
            else:
                if self.benchmark is not None:
                    label_text = f"{self.benchmark:.2f}"
                else:
                    label_text = " - "
                self.label.setText(label_text)
                self.displaying_benchmark = True
        return False


class SectionalWidget(QtWidgets.QWidget):
    def __init__(
            self, sectional: Union[str, float], benchmark: Optional[float], race_rank: int,
            meeting_rank: int, position: int):
        super(SectionalWidget, self).__init__()
        self.sectional = sectional
        self.benchmark = benchmark
        self.race_rank = race_rank
        self.meeting_rank = meeting_rank
        self.position = position
        self.displaying_benchmark = True

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: transparent;")
        score = 0
        if benchmark is not None and benchmark <= -1.5:
            score += 1
        if race_rank == 1:
            score += 1
        if meeting_rank != 0 and meeting_rank <= 5:
            score += 1
        if score == 3:
            self.setStyleSheet(self.styleSheet() + "color: #d503ff;")
        elif score == 2:
            self.setStyleSheet(self.styleSheet() + "color: red;")
        elif score == 1:
            self.setStyleSheet(self.styleSheet() + "color: orange;")
        if benchmark is not None:
            label_text = f"{benchmark:.1f}"
        else:
            label_text = " - "
        if position != 0:
            label_text += f" [{position}]"
        self.label = SmallInfoLabel(label_text)
        tooltip = ""
        if benchmark is not None:
            tooltip += f"Sectional Benchmark\n{benchmark:.1f}"
        if race_rank is not None:
            tooltip += f"\nRace Rank\n{race_rank}"
        if meeting_rank is not None:
            tooltip += f"\nMeeting Rank\n{meeting_rank}"
        self.label.setToolTip(tooltip)
        layout.addWidget(self.label)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and \
                event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.displaying_benchmark:
                if type(self.sectional) is float:
                    minutes, seconds = divmod(self.sectional, 60)
                    label_text = ""
                    if minutes > 0:
                        label_text += f"{minutes:.0f}:"
                    label_text += f"{seconds:.2f}"
                elif type(self.sectional) is str:
                    label_text = self.sectional
                self.displaying_benchmark = False
            else:
                if self.benchmark is not None:
                    label_text = f"{self.benchmark:.1f}"
                else:
                    label_text = " - "
                self.displaying_benchmark = True
            if self.position != 0:
                label_text += f" [{self.position}]"
            self.label.setText(label_text)
            return True
        return False


class RunsTitleWidget(QtWidgets.QWidget):
    def __init__(self):
        super(RunsTitleWidget, self).__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFont(QtGui.QFont(FONT, 10, weight=QtGui.QFont.Weight.Bold))
        self.setStyleSheet("background-color: transparent;")
        finish_pos_label = HeadingLabel("Position")
        finish_pos_label.setFixedWidth(screen_width_percentage(0.03))
        layout.addWidget(finish_pos_label)

        margin_label = HeadingLabel("Mar.")
        margin_label.setFixedWidth(screen_width_percentage(0.021))
        layout.addWidget(margin_label)

        venue_label = HeadingLabel("Venue")
        venue_label.setFixedWidth(screen_width_percentage(0.06))
        layout.addWidget(venue_label)

        date_label = HeadingLabel("Date")
        date_label.setFixedWidth(screen_width_percentage(0.04))
        layout.addWidget(date_label)

        distance_label = HeadingLabel("Dist.")
        distance_label.setFixedWidth(screen_width_percentage(0.028))
        layout.addWidget(distance_label)

        track_condition_label = HeadingLabel("Condition")
        track_condition_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(track_condition_label)

        weight_label = HeadingLabel("Weight")
        weight_label.setFixedWidth(screen_width_percentage(0.026))
        layout.addWidget(weight_label)

        jockey_label = HeadingLabel("Jockey")
        jockey_label.setFixedWidth(screen_width_percentage(0.063))
        layout.addWidget(jockey_label)

        price_label = HeadingLabel("Odds")
        price_label.setFixedWidth(screen_width_percentage(0.051))
        layout.addWidget(price_label)

        class_label = HeadingLabel("Class")
        class_label.setFixedWidth(screen_width_percentage(0.076))
        layout.addWidget(class_label)

        days_since_label = HeadingLabel("Between")
        days_since_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(days_since_label)

        l800_sectional_label = HeadingLabel("L800")
        l800_sectional_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(l800_sectional_label)

        l600_sectional_label = HeadingLabel("L600")
        l600_sectional_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(l600_sectional_label)

        l400_sectional_label = HeadingLabel("L400")
        l400_sectional_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(l400_sectional_label)

        l200_sectional_label = HeadingLabel("L200")
        l200_sectional_label.setFixedWidth(screen_width_percentage(0.025))
        layout.addWidget(l200_sectional_label)

        overall_time_label = HeadingLabel("R Time")
        overall_time_label.setFixedWidth(screen_width_percentage(0.04))
        layout.addWidget(overall_time_label)

        winner_time_label = HeadingLabel("W Time")
        winner_time_label.setFixedWidth(screen_width_percentage(0.03))
        layout.addWidget(winner_time_label)

        runner_tempo_label = HeadingLabel("R Temp.")
        runner_tempo_label.setFixedWidth(screen_width_percentage(0.031))
        layout.addWidget(runner_tempo_label)

        winner_tempo_label = HeadingLabel("W Temp.")
        winner_tempo_label.setFixedWidth(screen_width_percentage(0.032))
        layout.addWidget(winner_tempo_label)

        comment_label = HeadingLabel("")
        comment_label.setFixedWidth(screen_width_percentage(0.017))
        layout.addWidget(comment_label)


class RunsWidget(QtWidgets.QWidget):
    def __init__(self, run: Run, weight: float):
        super(RunsWidget, self).__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        if run.is_trial:
            self.setStyleSheet("background-color: #303c46; color: grey;")
        else:
            self.setStyleSheet("background-color: #444630;")

        finish_pos_label = SmallInfoLabel(
            f"{run.finish_position} of {run.starters}")
        finish_pos_label.setFixedWidth(screen_width_percentage(0.03))
        layout.addWidget(finish_pos_label)

        margin_label = SmallInfoLabel(run.margin)
        margin_label.setFixedWidth(screen_width_percentage(0.021))
        layout.addWidget(margin_label)

        venue_label = SmallInfoLabel(run.venue)
        venue_label.setFixedWidth(screen_width_percentage(0.06))
        layout.addWidget(venue_label)

        date_label = SmallInfoLabel(run.meeting_date)
        date_label.setFixedWidth(screen_width_percentage(0.04))
        layout.addWidget(date_label)

        distance_label = SmallInfoLabel(f"{run.distance}m")
        distance_label.setFixedWidth(screen_width_percentage(0.028))
        layout.addWidget(distance_label)

        track_condition_label = SmallInfoLabel(run.track_condition)
        track_condition_label.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(track_condition_label)

        if not run.is_trial:
            if run.weight is None:
                weight_label = SmallInfoLabel(" - ")
            else:
                weight_label = SmallInfoLabel(f"{run.weight}kg")
                if run.weight - weight >= 6:
                    weight_label.setStyleSheet("color: #d503ff;")
                elif run.weight - weight >= 4:
                    weight_label.setStyleSheet("color: red;")
                elif run.weight - weight >= 2:
                    weight_label.setStyleSheet("color: orange;")
            weight_label.setFixedWidth(screen_width_percentage(0.026))
            layout.addWidget(weight_label)

        jockey_label = SmallInfoLabel(run.jockey.name)
        jockey_label.setFixedWidth(screen_width_percentage(0.063))
        layout.addWidget(jockey_label)

        if not run.is_trial:
            if run.fluctuation is None:
                price_label = SmallInfoLabel(
                    f"${run.open_price}/${run.starting_price}")
            else:
                price_label = SmallInfoLabel(
                    f"${run.open_price}/${run.fluctuation}/${run.starting_price}")
            price_label.setFixedWidth(screen_width_percentage(0.051))
            layout.addWidget(price_label)

            class_text = run._class[:17]
            class_label = SmallInfoLabel(class_text)
            if run.is_class:
                class_label.setStyleSheet("color: yellow;")
            class_label.setFixedWidth(screen_width_percentage(0.076))
            layout.addWidget(class_label)

            days_since_label = SmallInfoLabel(f"{run.days_since_last} days")
            days_since_label.setFixedWidth(screen_width_percentage(0.035))
            layout.addWidget(days_since_label)
            layout.addSpacerItem(QtWidgets.QSpacerItem(2, 0))

        if not run.is_trial:
            if run.splits.runner_split_l600 is None or run.splits.runner_split_l400 is None or \
                    run.splits.runner_split_l200 is None or run.splits.runner_split_finish is None:
                l800_sectional = " - "
            else:
                l800_sectional = run.splits.runner_split_l600 + run.splits.runner_split_l400 + \
                    run.splits.runner_split_l200 + run.splits.runner_split_finish

            l800_position = 0
            for position_summary in run.position_summaries:
                if position_summary.distance == 800:
                    if position_summary.position is not None:
                        l800_position = position_summary.position
                        break
            l800_sectional_label = SectionalWidget(
                l800_sectional, run.form_benchmark.runner_time_difference_l800,
                run.form_benchmark.runner_race_position_l800,
                run.form_benchmark.runner_meeting_position_l800,
                l800_position)
            l800_sectional_label.setFixedWidth(screen_width_percentage(0.035))
            layout.addWidget(l800_sectional_label)

            if run.splits.runner_split_l600 is None or run.splits.runner_split_l400 is None or \
                    run.splits.runner_split_finish is None:
                l600_sectional = " - "
            else:
                l600_sectional = run.splits.runner_split_l400 + run.splits.runner_split_l200 + \
                    run.splits.runner_split_finish
            l600_position = 0
            for position_summary in run.position_summaries:
                if position_summary.distance == 600:
                    if position_summary.position is not None:
                        l600_position = position_summary.position
                        break

            l600_sectional_label = SectionalWidget(
                l600_sectional, run.form_benchmark.runner_time_difference_l600,
                run.form_benchmark.runner_race_position_l600,
                run.form_benchmark.runner_meeting_position_l600,
                l600_position)
            l600_sectional_label.setFixedWidth(screen_width_percentage(0.035))
            layout.addWidget(l600_sectional_label)

            if run.splits.runner_split_l400 is None or run.splits.runner_split_finish is None:
                l400_sectional = " - "
            else:
                l400_sectional = run.splits.runner_split_l200 + run.splits.runner_split_finish
            l400_position = 0
            for position_summary in run.position_summaries:
                if position_summary.distance == 400:
                    if position_summary.position is not None:
                        l400_position = position_summary.position
                        break
            l400_sectional_label = SectionalWidget(
                l400_sectional, run.form_benchmark.runner_time_difference_l400,
                run.form_benchmark.runner_race_position_l400,
                run.form_benchmark.runner_meeting_position_l400,
                l400_position)
            l400_sectional_label.setFixedWidth(screen_width_percentage(0.035))
            layout.addWidget(l400_sectional_label)

            if run.splits.runner_split_finish is None:
                l200_sectional = " - "
            else:
                l200_sectional = run.splits.runner_split_finish
            l200_position = 0
            for position_summary in run.position_summaries:
                if position_summary.distance == 200:
                    if position_summary.position is not None:
                        l200_position = position_summary.position
                        break
            l200_sectional_label = SectionalWidget(
                l200_sectional, run.form_benchmark.runner_time_difference_l200,
                run.form_benchmark.runner_race_position_l200,
                run.form_benchmark.runner_meeting_position_l200,
                l200_position)
            l200_sectional_label.setFixedWidth(screen_width_percentage(0.025))
            layout.addWidget(l200_sectional_label)

            overall_time_label = SectionalWidget(
                run.finish_time, run.form_benchmark.runner_time_difference, 0, 0,
                run.finish_position)
            overall_time_label.setFixedWidth(screen_width_percentage(0.04))
            layout.addWidget(overall_time_label)

            if run.winner_time is not None and len(run.winner_time) > 0:
                run.winner_time = run.winner_time[:-1]
                if run.winner_time[0] == "0":
                    run.winner_time = run.winner_time[1:]
                winner_time_label = SectionalWidget(
                    run.winner_time, run.form_benchmark.winner_time_difference, 0, 0, 0)
                winner_time_label.setFixedWidth(screen_width_percentage(0.03))
                layout.addWidget(winner_time_label)

            runner_tempo_label = TempoWidget(
                run.form_benchmark.runner_tempo_difference,
                run.form_benchmark.runner_tempo_label)
            runner_tempo_label.setFixedWidth(screen_width_percentage(0.03))
            layout.addWidget(runner_tempo_label)

            winner_tempo_label = TempoWidget(
                run.form_benchmark.leader_tempo_difference,
                run.form_benchmark.leader_tempo_label)
            winner_tempo_label.setFixedWidth(screen_width_percentage(0.03))
            layout.addWidget(winner_tempo_label)

            comment_icon = QtGui.QIcon("icons/comment.png")
            comment_icon_label = QtWidgets.QLabel()
            comment_icon_label.setStyleSheet("background-color: transparent;")
            comment_icon_label.setPixmap(
                comment_icon.pixmap(screen_height_percentage(0.02),
                                    screen_width_percentage(0.02)))
            tooltip = ""
            if run.video_comment is not None:
                tooltip += f"Video Comment\n{run.video_comment}"
            if run.video_note is not None:
                tooltip += f"\n\nVideo Note\n{run.video_note}"
            comment_icon_label.setToolTip(tooltip)
            comment_icon_label.setFixedWidth(screen_width_percentage(0.02))
            layout.addWidget(comment_icon_label)

        layout.addStretch()


class SpellWidget(QtWidgets.QWidget):
    def __init__(self, days_since_last: int):
        super(SpellWidget, self).__init__()
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)
        days_since_label = HeadingLabel(f"Spell {days_since_last} days")
        days_since_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        hline_start = QHLine()
        hline_start.setStyleSheet(
            hline_start.styleSheet() + "border-radius: 2;")
        layout.addWidget(hline_start)
        layout.addWidget(days_since_label)
        hline_end = QHLine()
        hline_end.setStyleSheet(
            hline_end.styleSheet() + "border-radius: 2;")
        layout.addWidget(hline_end)


class SelectionWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, selection: Selection, venue: str):
        super(SelectionWidget, self).__init__()
        self.selection = selection
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)
        name_label = LargeInfoLabel(f"{selection.number}. {selection.name}")
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        name_label.setFixedWidth(screen_width_percentage(0.15))
        layout.addWidget(name_label)
        weight_string = f"{selection.weight}kg"
        if selection.claim != 0:
            weight_string += f" (a{selection.claim})"
        runs_widget = SmallInfoLabel(
            f"{selection.total_runs}:{selection.total_wins}-{selection.total_places}")
        runs_widget.setFixedWidth(screen_width_percentage(0.035))
        layout.addWidget(
            runs_widget,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        weight_label = SmallInfoLabel(weight_string)
        weight_label.setFixedWidth(screen_width_percentage(0.048))
        layout.addWidget(
            weight_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        barrier_label = SmallInfoLabel(f"{selection.barrier}")
        barrier_label.setFixedWidth(screen_width_percentage(0.02))
        layout.addWidget(
            barrier_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        trainer_label_text = "T: " + selection.trainer.name
        if selection.trainer.location is not None:
            match_ratio = SequenceMatcher(
                None, selection.trainer.location, venue).ratio()
            if match_ratio > 0.8:
                trainer_label_text += " [H]"
        trainer_label = SmallInfoLabel(trainer_label_text)
        score = 0
        if selection.trainer.last_year_win_percentage is not None and \
                selection.trainer.last_year_win_percentage >= 0.18:
            score += 1
        if selection.trainer_jockey_win_percentage is not None and \
                selection.trainer_jockey_win_percentage >= 20:
            score += 1
        if score == 1:
            trainer_label.setStyleSheet(
                trainer_label.styleSheet() + "color: orange;")
        elif score == 2:
            trainer_label.setStyleSheet(
                trainer_label.styleSheet() + "color: red;")
        tooltip = ""
        if selection.trainer.last_year_win_percentage is not None:
            tooltip += f"Last Year Win Percentage\n{selection.trainer.last_year_win_percentage*100:.0f}%"
        if selection.trainer.last_year_place_percentage is not None:
            tooltip += f"\nLast Year Place Percentage\n{selection.trainer.last_year_place_percentage*100:.0f}%"
        if selection.trainer_jockey_win_percentage is not None:
            tooltip += f"\nTrainer Jockey Win Percentage\n{selection.trainer_jockey_win_percentage:.0f}%"
        trainer_label.setToolTip(tooltip)
        trainer_label.setFixedWidth(screen_width_percentage(0.1))
        layout.addWidget(
            trainer_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        jockey_label = SmallInfoLabel("J: " + selection.jockey.name)
        score = 0
        if selection.jockey.last_year_win_percentage is not None and \
                selection.jockey.last_year_win_percentage >= 0.14:
            score += 1
        if selection.trainer_jockey_win_percentage is not None and \
                selection.trainer_jockey_win_percentage >= 20:
            score += 1
        if score == 1:
            jockey_label.setStyleSheet(
                jockey_label.styleSheet() + "color: orange;")
        elif score == 2:
            jockey_label.setStyleSheet(
                jockey_label.styleSheet() + "color: red;")
        jockey_label.setFixedWidth(screen_width_percentage(0.09))
        tooltip = ""
        if selection.jockey.last_year_win_percentage is not None:
            tooltip += f"Last Year Win Percentage\n{selection.jockey.last_year_win_percentage*100:.0f}%"
        if selection.jockey.last_year_place_percentage is not None:
            tooltip += f"\nLast Year Place Percentage\n{selection.jockey.last_year_place_percentage*100:.0f}%"
        if selection.trainer_jockey_win_percentage is not None:
            tooltip += f"\nTrainer Jockey Win Percentage\n{selection.trainer_jockey_win_percentage:.0f}%"
        jockey_label.setToolTip(tooltip)
        layout.addWidget(
            jockey_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        speed_position = selection.prediction.normalized_speed_position
        if speed_position is not None:
            speed_position = speed_position.capitalize()
        speed_position_label = SmallInfoLabel(speed_position)
        speed_position_label.setFixedWidth(screen_width_percentage(0.053))
        layout.addWidget(speed_position_label,
                         alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        # get all bet365 win odds
        odds = [odds.price for odds in selection.odds
                if odds.bet_type == "Win"]
        if len(odds) > 0:
            win_odds = odds[0]
        else:
            win_odds = 0.00

        odds = [odds.price for odds in selection.odds
                if odds.bet_type == "Place"]
        if len(odds) > 0:
            place_odds = odds[0]
        else:
            place_odds = 0.00
        if win_odds > 20:
            win_odds_string = f"${win_odds:.0f}"
        else:
            win_odds_string = f"${win_odds:.2f}"
        if place_odds > 20:
            place_odds_string = f"${place_odds:.0f}"
        else:
            place_odds_string = f"${place_odds:.2f}"
        odds_label = SmallInfoLabel(f"{win_odds_string}\t{place_odds_string}")
        odds_label.setFixedWidth(screen_width_percentage(0.07))
        layout.addWidget(
            odds_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        roi_label = SmallInfoLabel(f"ROI: {selection.roi:.0f}%")
        if selection.roi > 0:
            roi_label.setStyleSheet(roi_label.styleSheet() + "color: orange;")
        roi_label.setFixedWidth(screen_width_percentage(0.052))
        layout.addWidget(
            roi_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        def ordinal(n): return "%d%s" % (
            n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
        prep_label = SmallInfoLabel(
            f"{ordinal(selection.runs_since_spell + 1)} up")
        prep_label.setFixedWidth(screen_width_percentage(0.035))
        score = 0
        win_percentage, average_difference, max_difference = \
            selection.preparation_stats.get_preparation_stats(
                selection.runs_since_spell)
        if win_percentage is not None and win_percentage >= 0.33:
            score += 1
        if average_difference is not None and average_difference <= -1:
            score += 1
        if max_difference is not None and max_difference <= -1.5 and \
                selection.runs_since_spell < 3:
            score += 1
        if score == 1:
            prep_label.setStyleSheet(
                prep_label.styleSheet() + "color: orange;")
        elif score == 2:
            prep_label.setStyleSheet(
                prep_label.styleSheet() + "color: red;")
        elif score == 3:
            prep_label.setStyleSheet(
                prep_label.styleSheet() + "color: #d503ff;")
        tooltip = ""
        if win_percentage is not None:
            tooltip += f"Win Percentage\n{win_percentage*100:.0f}%"
        if average_difference is not None:
            tooltip += f"\nAverage Difference\n{average_difference:.2f}"
        if max_difference is not None:
            tooltip += f"\nMax Difference\n{max_difference:.2f}"
        prep_label.setToolTip(tooltip)
        layout.addWidget(
            prep_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        if selection.days_since_last is None or selection.days_since_last == 0:
            days_since_label = SmallInfoLabel("Unraced")
        else:
            days_since_label = SmallInfoLabel(
                f"{selection.days_since_last} days")
        days_since_label.setFixedWidth(screen_width_percentage(0.047))
        layout.addWidget(
            days_since_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        comment_icon = QtGui.QIcon("icons/comment.png")
        comment_icon_label = QtWidgets.QLabel()
        comment_icon_label.setStyleSheet("background-color: transparent;")
        comment_icon_label.setPixmap(
            comment_icon.pixmap(screen_height_percentage(0.02),
                                screen_width_percentage(0.02)))
        tooltip = ""
        if selection.comments is not None:
            tooltip += f"General Comments\n{selection.comments}"
        for brand, comment in selection.external_comments.items():
            tooltip += f"\n\n{brand.capitalize()}\n{comment}"
        comment_icon_label.setToolTip(tooltip)
        comment_icon_label.setFixedWidth(screen_width_percentage(0.02))
        layout.addWidget(comment_icon_label)

        gear_icon = QtGui.QIcon("icons/horse_halter.png")
        gear_icon_label = QtWidgets.QLabel()
        gear_icon_label.setStyleSheet("background-color: transparent;")
        gear_icon_label.setPixmap(
            gear_icon.pixmap(screen_height_percentage(0.022),
                             screen_width_percentage(0.022)))
        if selection.gear_changes is None or selection.gear_changes == "":
            gear_icon_label.setToolTip("No Gear Changes")
        else:
            gear_icon_label.setToolTip(selection.gear_changes)
        gear_icon_label.setFixedWidth(screen_width_percentage(0.022))
        layout.addWidget(gear_icon_label)

        layout.addStretch()
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and \
                event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
            return True
        return False


class SelectionsWidget(QtWidgets.QWidget):
    def __init__(self, selections: list[Selection], venue: str):
        super(SelectionsWidget, self).__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(screen_height_percentage(0.69))
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QVBoxLayout()
        layout.stretch(0)
        layout.setSpacing(0)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.setIndentation(0)

        self.sections: list[tuple[Selection, QtWidgets.QWidget]] = []
        self.define_sections(selections)
        self.add_sections(venue)

    def add_sections(self, venue: str):
        for (selection, widget) in self.sections:
            button1 = self.add_button(selection, venue)
            section1 = self.add_widget(button1, widget)
            button1.addChild(section1)

    def define_sections(self, selections: list[Selection]):
        for selection in selections:
            widget = QtWidgets.QWidget(self.tree)
            layout = QtWidgets.QVBoxLayout(widget)
            widget.setLayout(layout)
            if selection.total_runs != 0:
                layout.addWidget(RunsTitleWidget())

            to_date = datetime.now()
            for run in selection.runs[:10]:
                from_date = datetime.strptime(run.meeting_date, "%Y-%m-%d")
                if (to_date - from_date).days > SPELL_THRESHOLD:
                    layout.addWidget(SpellWidget((to_date - from_date).days))
                to_date = from_date
                run_widget = RunsWidget(
                    run, selection.weight - selection.claim)
                layout.addWidget(run_widget)
            self.sections.append((selection, widget))

    def add_button(self, selection: Selection, venue: str):
        item = QtWidgets.QTreeWidgetItem()
        count = self.tree.topLevelItemCount()
        if count % 2 == 0:
            item.setBackground(0, QtGui.QColor(84, 104, 122))
        else:
            item.setBackground(0, QtGui.QColor(74, 94, 112))
        self.tree.addTopLevelItem(item)
        expand_button = SelectionWidget(selection, venue)
        expand_button.clicked.connect(lambda: self.on_clicked(item))
        self.tree.setItemWidget(item, 0, expand_button)
        return item

    def on_clicked(self, item):
        if item.isExpanded():
            item.setExpanded(False)
        else:
            item.setExpanded(True)

    def add_widget(self, button, widget):
        section = QtWidgets.QTreeWidgetItem(button)
        section.setDisabled(True)
        self.tree.setItemWidget(section, 0, widget)
        return section


class EventInfoWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventInfoWidget, self).__init__()
        self.setMaximumHeight(24)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(SmallInfoLabel(event.name))
        layout.addWidget(QVLine())
        self.time_remaining_label = SmallInfoLabel(
            self.get_time_remaining(datetime.strptime(event.time, "%I:%M %p")))
        layout.addWidget(self.time_remaining_label)
        layout.addWidget(QVLine())
        layout.addWidget(SmallInfoLabel(f"{event.distance}m"))
        layout.addWidget(QVLine())
        layout.addWidget(SmallInfoLabel(f"${event.prize_money:,}"))
        layout.addWidget(QVLine())
        layout.addWidget(SmallInfoLabel(
            f"{round(event.pace, 2)} Pace Rating"))
        layout.addWidget(QVLine())
        layout.addWidget(SmallInfoLabel(f"{event.starters} Runners"))
        layout.addWidget(QVLine())
        layout.addWidget(SmallInfoLabel(f"{event._class} Class"))
        layout.addWidget(QVLine())
        layout.addStretch()
        self.tick_timer = EventTickTimer(event)
        self.tick_timer.timeout.connect(self.update_time_remaining)
        self.tick_timer.start(1000)

    def get_time_remaining(self, event_time: datetime) -> str:
        current_time = datetime.now()
        event_time = event_time.replace(
            year=current_time.year, month=current_time.month,
            day=current_time.day)
        if event_time < current_time:
            timedelta_remaining = current_time - event_time
            hours = -timedelta_remaining.seconds // 3600
            minutes = -timedelta_remaining.seconds % 3600 // 60
            seconds = -timedelta_remaining.seconds % 60
        else:
            timedelta_remaining = event_time - current_time
            hours = timedelta_remaining.seconds // 3600
            minutes = timedelta_remaining.seconds % 3600 // 60
            seconds = timedelta_remaining.seconds % 60
        if hours == 0 and minutes == 0:
            time_remaining = f"{seconds}s"
        elif hours == 0:
            time_remaining = f"{minutes}m {seconds}s"
        else:
            time_remaining = f"{hours}h {minutes}m"
        return time_remaining

    def update_time_remaining(self):
        self.time_remaining_label.setText(
            self.get_time_remaining(self.tick_timer.event_time))
        self.tick_timer.start(1000)


class EventWidget(QtWidgets.QWidget):
    def __init__(self, event: Event, venue: str):
        super(EventWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(EventInfoWidget(event), 0)
        layout.addWidget(
            SelectionsWidget(event.selections, venue), 1,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop)


class EventsTabWidget(QtWidgets.QTabWidget):
    def __init__(self, meeting: Meeting):
        super(EventsTabWidget, self).__init__()
        self.tabBar().hide()
        self.setContentsMargins(0, 0, 0, 0)
        for event in meeting.events:
            event_widget = EventWidget(event, meeting.name)
            self.addTab(event_widget, event.name)


class EventNumberWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventNumberWidget, self).__init__()

        self.event_number = event.event_number
        event_layout = QtWidgets.QVBoxLayout()
        self.setLayout(event_layout)
        event_button = QtWidgets.QPushButton(
            f"{self.event_number}")
        event_button.setFont(QtGui.QFont(
            FONT, 16, weight=QtGui.QFont.Weight.Bold))
        event_button.setCursor(QtGui.QCursor(
            QtCore.Qt.CursorShape.PointingHandCursor))
        # make button circular
        event_button.setStyleSheet(
            f"border-radius: 5;")
        event_button.setFixedWidth(screen_width_percentage(0.04))
        event_button.setFixedHeight(screen_height_percentage(0.04))
        event_button.clicked.connect(self.button_clicked)
        event_label = LargeInfoLabel(f"{event.time}")
        event_layout.addWidget(
            event_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        event_layout.addWidget(event_label)
        event_layout.addStretch()

    def button_clicked(self):
        event_parent = self.parent()
        if type(event_parent) is EventNumbersWidget:
            event_parent.reset_background()
        self.setStyleSheet("background-color: #303c46;")
        events_parent = event_parent.parent()
        if type(events_parent) is EventsInfoWidget:
            events_parent.set_tab_index(self.event_number - 1)


class EventNumbersWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(EventNumbersWidget, self).__init__()

        events_layout = QtWidgets.QHBoxLayout()
        self.setLayout(events_layout)
        events_layout.setContentsMargins(0, 0, 0, 0)
        for event in meeting.events:
            event_widget = EventNumberWidget(event)
            if event.event_number == 1:
                event_widget.setStyleSheet("background-color: #303c46;")
            events_layout.addWidget(event_widget)
        events_layout.addStretch()

    def reset_background(self):
        layout = self.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue
            widget.setStyleSheet("background-color: #54687a;")


class SelectionGraphWidget(QtWidgets.QWidget):
    def __init__(self, value: float, max_value: float, number: int):
        super(SelectionGraphWidget, self).__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = SmallInfoLabel(number)
        # set width so all labels are the same size
        label.setFixedWidth(screen_width_percentage(0.016))
        layout.addWidget(label)
        layout.addWidget(HorizontalBar(
            value, max_value), alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        if value > 1000:
            value = numerize.numerize(value, 1)
        layout.addWidget(VerySmallInfoLabel(value))
        layout.addStretch()


class EventStatsWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventStatsWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SubtitleLabel("Train/Jock Win %"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            event.selections, key=lambda x: x.trainer_jockey_win_percentage,
            reverse=True)
        selections = selections[:9]
        for selection in selections:
            value = selection.trainer_jockey_win_percentage
            layout.addWidget(
                SelectionGraphWidget(value, 70, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Avg. Prize Money"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            event.selections, key=lambda x: x.average_prize_money, reverse=True)
        selections = selections[:9]
        max_value = max([x.average_prize_money for x in selections]) * 1.1
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.average_prize_money
            if value is None:
                value = 0.0
            layout.addWidget(
                SelectionGraphWidget(value, max_value, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("wWet W/P %"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        weighted_wet_win_place_values = []
        for selection in selections:
            weighted_wet_win_place = (
                selection.wet_runs_win_percentage * 2 + selection.wet_runs_place_percentage) / 3
            weighted_wet_win_place_values.append(
                (selection.number, weighted_wet_win_place))
        weighted_wet_win_place_values.sort(key=lambda x: x[1], reverse=True)
        weighted_wet_win_place_values = weighted_wet_win_place_values[:9]
        # graph based on barrier and predicted speed values
        for wet_win_place in weighted_wet_win_place_values:
            if wet_win_place[1] is None:
                wet_win_place[1] = 0.0
            layout.addWidget(
                SelectionGraphWidget(
                    wet_win_place[1],
                    100, wet_win_place[0]),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)


class EventSpeedWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventSpeedWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SubtitleLabel("Early Speed"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(event.selections, key=lambda x: x.barrier)
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.prediction.normalized_speed
            layout.addWidget(
                SelectionGraphWidget(value, 1.0, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Finish Speed"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.prediction.finish_speed
            if value is None:
                value = 0.0
            layout.addWidget(
                SelectionGraphWidget(value, 1.0, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)


class EventModelWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventModelWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SubtitleLabel("Punter Edge"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = event.selections
        for selection in selections:
            if selection.punters_edge is None:
                selection.punters_edge = 0.0
            if selection.prediction.model_output is None:
                selection.prediction.model_output = 0.0
            if selection.prediction.winning_chance is None:
                selection.prediction.winning_chance = 0.0
        selections.sort(key=lambda x: x.punters_edge, reverse=True)
        selections = selections[:9]
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.punters_edge
            layout.addWidget(
                SelectionGraphWidget(value, 1.0, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Model Output"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            selections, key=lambda x: x.prediction.model_output, reverse=True)[:9]
        max_value = max([x.prediction.model_output for x in selections]) * 1.1
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.prediction.model_output
            layout.addWidget(
                SelectionGraphWidget(value, max_value, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Winning Chance"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            selections, key=lambda x: x.prediction.winning_chance, reverse=True)[:9]
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.prediction.winning_chance
            layout.addWidget(
                SelectionGraphWidget(value, 0.85, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop)


class EventAnalysisWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventAnalysisWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setFixedWidth(screen_width_percentage(0.12))
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        combo_box = QtWidgets.QComboBox()
        combo_box.addItem("Model Analysis")
        combo_box.addItem("Speed Analysis")
        combo_box.addItem("Stats Analysis")
        layout.addWidget(combo_box)
        combo_box.currentIndexChanged.connect(
            lambda index: self.change_analysis(index, event))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        layout.addWidget(EventModelWidget(event))

    def change_analysis(self, index: int, event: Event):
        layout = self.layout()
        if layout is None:
            return
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is None:
                continue
            elif type(item.widget()) is QtWidgets.QComboBox:
                continue
            elif item.widget() is None:
                continue
            item.widget().setParent(None)
        if index == 0:
            layout.addWidget(EventModelWidget(event))
        elif index == 1:
            layout.addWidget(EventSpeedWidget(event))
        elif index == 2:
            layout.addWidget(EventStatsWidget(event))


class EventsInfoWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(EventsInfoWidget, self).__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            EventNumbersWidget(meeting),
            alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.event_tab_widget = EventsTabWidget(meeting)
        layout.addWidget(
            self.event_tab_widget, 1,
            QtCore.Qt.AlignmentFlag.AlignTop)

    def set_tab_index(self, index: int):
        self.event_tab_widget.setCurrentIndex(index)
        parent = self.parent()
        if type(parent) is EventsWidget:
            parent.change_race(index)


class EventsWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(EventsWidget, self).__init__()

        self.meeting = meeting
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(EventsInfoWidget(self.meeting))
        layout.addWidget(
            EventAnalysisWidget(self.meeting.events[0]),
            alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def change_race(self, event_number: int):
        layout = self.layout()
        if layout is None:
            return
        item = layout.itemAt(layout.count() - 1)
        if item is None:
            return
        item.widget().setParent(None)
        if type(layout) is QtWidgets.QHBoxLayout:
            layout.addWidget(
                EventAnalysisWidget(self.meeting.events[event_number]),
                alignment=QtCore.Qt.AlignmentFlag.AlignRight)


class MeetingInfoWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(MeetingInfoWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setFixedWidth(screen_width_percentage(0.1))

        layout.addWidget(SubtitleLabel(f"Track"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(meeting.name))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel(f"Rail Position"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(meeting.rail_position))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        track_condition = meeting.events[0].track_condition
        track_type = meeting.events[0].track_type
        weather = meeting.events[0].weather

        layout.addWidget(SubtitleLabel(f"Condition"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(track_condition))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel(f"Track Type"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(track_type))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel(f"Weather"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(weather.capitalize()))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))
        layout.addStretch()


class MeetingsTab(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(MeetingsTab, self).__init__()
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 5, 0)
        meeting_info_widget = MeetingInfoWidget(meeting)
        events_widget = EventsWidget(meeting)
        layout.addWidget(meeting_info_widget)
        layout.addWidget(events_widget)


class ScraperTab(QtWidgets.QScrollArea):
    def __init__(self, scraper: MeetingsScraper):
        super(ScraperTab, self).__init__()

        self.scraper = scraper
        self.meetings: list[Meeting] = []
        main_widget = QtWidgets.QWidget()
        self.setStyleSheet(
            'QScrollArea {border: 0px;}')
        self.setLayout(QtWidgets.QFormLayout())
        horizontal_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(horizontal_layout)
        self.setWidget(main_widget)
        self.setWidgetResizable(True)

        date_widget = QtWidgets.QWidget()
        date_widget.setFixedWidth(screen_width_percentage(0.12))
        date_form = QtWidgets.QFormLayout()
        date_widget.setLayout(date_form)
        label = LargeInfoLabel("Date to Scrape")
        font = QtGui.QFont(FONT, 16, weight=QtGui.QFont.Weight.Bold)
        font.setUnderline(True)
        label.setFont(font)

        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        date_form.addRow(label)
        self.date_selector = QtWidgets.QDateEdit()
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setDate(QtCore.QDate.currentDate())
        date_form.addWidget(self.date_selector)
        self.scrape_button = QtWidgets.QPushButton("Extract")
        date_form.addWidget(self.scrape_button)
        self.scrape_button.clicked.connect(
            lambda: self.scrape_date(self.date_selector.date()))
        self.local_checkbox = QtWidgets.QCheckBox("Use local data")
        self.local_checkbox.setChecked(True)
        date_form.addWidget(self.local_checkbox)

        meetings_widget = QtWidgets.QScrollArea()
        meetings_widget.setWidgetResizable(True)
        meetings_group = QtWidgets.QGroupBox()
        meetings_widget.setWidget(meetings_group)
        meetings_widget.setStyleSheet("QGroupBox {border: 0px;}")
        self.meetings_form = QtWidgets.QFormLayout()
        meetings_group.setLayout(self.meetings_form)
        horizontal_layout.addWidget(date_widget, 1)
        horizontal_layout.addWidget(meetings_widget, 1)
        # add horizontal space for the rest of the window
        horizontal_layout.addStretch()

    def scrape_date(self, date: QtCore.QDate):
        # clear the previous tabs
        tab_widget = self.parent().parent()
        if type(tab_widget) is QtWidgets.QTabWidget:
            for i in reversed(range(tab_widget.count())):
                if tab_widget.tabText(i) != "Home":
                    tab_widget.removeTab(i)

        # clear the previous meetings
        for i in reversed(range(self.meetings_form.count())):
            self.meetings_form.itemAt(i).widget().setParent(None)
        self.scrape_button.setEnabled(False)
        self.scrape_button.setText("Extracting...")
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.update()

        if self.local_checkbox.isChecked():
            with open("meetings.txt", "r") as file:
                self.meetings = []
                for line in file.readlines():
                    self.meetings.append(eval(line))
        else:
            scrape_date = datetime(date.year(), date.month(), date.day())
            self.meetings = self.scraper.get_meetings(scrape_date)
            with open("meetings.txt", "w") as file:
                for meeting in self.meetings:
                    file.write(str(meeting) + "\n")

        state_dict = group_by_state(self.meetings)
        for state, meetings in state_dict.items():
            state_frame = self.create_state_frame(state, meetings)
            self.meetings_form.addWidget(state_frame)

        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.scrape_button.setText("Extract")
        self.scrape_button.setEnabled(True)

    def create_state_frame(
            self, state: str, meetings: list[Meeting]) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout()
        frame.setLayout(layout)
        title_label = TitleLabel(state)
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_label)
        layout.addWidget(QHLine())
        state_widget = QtWidgets.QWidget()
        horizontal_layout = QtWidgets.QHBoxLayout()
        state_widget.setLayout(horizontal_layout)
        for meeting in meetings:
            meeting_name = meeting.name
            button = QtWidgets.QPushButton(meeting_name)
            button.setFixedWidth(screen_width_percentage(0.095))
            button.setCursor(QtGui.QCursor(
                QtCore.Qt.CursorShape.PointingHandCursor))
            button.clicked.connect(self.open_meeting_window)
            button.setFixedHeight(screen_height_percentage(0.04))
            horizontal_layout.addWidget(button)

        horizontal_layout.addStretch()
        layout.addWidget(state_widget)
        return frame

    def open_meeting_window(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        sender = self.sender()
        if type(sender) is not QtWidgets.QPushButton:
            return
        sender.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.update()
        meeting_name = sender.text()
        meeting = next(
            (meeting for meeting in self.meetings
             if meeting.name == meeting_name))
        tab_widget = self.parent().parent()
        if type(tab_widget) is QtWidgets.QTabWidget:
            # check if the tab widget already exists
            tab_index = -1
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) == meeting.name:
                    tab_index = i
                    break
            if tab_index == -1:
                tab_index = tab_widget.addTab(
                    MeetingsTab(meeting), meeting.name)
            tab_widget.setCurrentIndex(tab_index)
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            sender.setCursor(QtGui.QCursor(
                QtCore.Qt.CursorShape.PointingHandCursor))
            return

        print("Error: Tab widget not found")
        self.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, scraper: MeetingsScraper):
        super(MainWindow, self).__init__()

        widget = QtWidgets.QTabWidget()
        self.setCentralWidget(widget)
        window_layout = QtWidgets.QFormLayout()
        widget.setLayout(window_layout)
        widget.setContentsMargins(10, 10, 0, 0)

        widget.setMaximumSize(SCREEN_SIZE)

        widget.addTab(ScraperTab(scraper), "Home")
        widget.setTabsClosable(True)
        widget.tabCloseRequested.connect(lambda index: widget.removeTab(index))
        # remove border inside tabs
        widget.setStyleSheet("QTabWidget::pane {border: 0;}")


class MeetingScraperApp(QtWidgets.QApplication):
    def __init__(self):
        super(MeetingScraperApp, self).__init__(sys.argv)

        self.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
        self.setApplicationName("Meeting Scraper")
        self.setApplicationDisplayName("Meeting Scraper")

        app_font = QtGui.QFont()
        app_font.setFamily("Helvetica")
        app_font.setPointSize(14)

        self.setFont(app_font)

    def run(self, scraper: MeetingsScraper) -> int:
        global SCREEN_SIZE
        SCREEN_SIZE = QtWidgets.QApplication.primaryScreen().size()
        if SCREEN_SIZE.width() > 1920:
            SCREEN_SIZE.setWidth(1920)
        if SCREEN_SIZE.height() > 1080:
            SCREEN_SIZE.setHeight(1080)
        window = MainWindow(scraper)
        window.showMaximized()

        return self.exec_()
