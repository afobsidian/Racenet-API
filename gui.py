# ruff: noqa: F401
from __future__ import annotations

import sys
from datetime import datetime
from difflib import SequenceMatcher
from textwrap import shorten
from typing import Callable, Optional, Union, cast

import qdarkstyle  # type: ignore[import-untyped]
from numerize import numerize  # type: ignore[import-untyped]
from PySide6 import QtCore, QtGui, QtWidgets

from app_state import AppState, meeting_key
from meetings_data import (
    SPELL_THRESHOLD,
    Event,
    FormBenchmark,
    Jockey,
    Meeting,
    Odds,
    OddsFluctuation,
    PositionSummary,
    Prediction,
    PreparationStats,
    Run,
    Selection,
    Splits,
    Trainer,
    group_by_state,
)
from scraper import MeetingsScraper
from workers import MeetingsLoadWorker

SCREEN_SIZE = QtCore.QSize()
FONT = "Helvetica"
BASE_FONT_POINT_SIZE = 12
ANALYSIS_VIEWS: list[tuple[str, str, Callable[[Event], QtWidgets.QWidget]]] = []


def screen_width_percentage(percentage: float) -> int:
    return int(SCREEN_SIZE.width() * percentage)


def screen_height_percentage(percentage: float) -> int:
    return int(SCREEN_SIZE.height() * percentage)


def scaled_font_size(point_size: int) -> int:
    app = QtWidgets.QApplication.instance()
    if not isinstance(app, QtWidgets.QApplication):
        return point_size

    base_size = app.font().pointSizeF()
    if base_size <= 0:
        return point_size

    scale = max(1.0, base_size / BASE_FONT_POINT_SIZE)
    return max(point_size, round(point_size * scale))


def build_font(
    point_size: int,
    weight: QtGui.QFont.Weight = QtGui.QFont.Weight.Normal,
) -> QtGui.QFont:
    return QtGui.QFont(FONT, scaled_font_size(point_size), weight=weight)


def monitor_font_point_size(screen: Optional[QtGui.QScreen]) -> int:
    if screen is None:
        return BASE_FONT_POINT_SIZE

    geometry = screen.availableGeometry().size()
    geometry_scale = min(
        geometry.width() / 1600 if geometry.width() else 1.0,
        geometry.height() / 900 if geometry.height() else 1.0,
    )
    dpi_scale = screen.logicalDotsPerInch() / 96 if screen.logicalDotsPerInch() else 1.0
    scale = min(max(1.0, max(geometry_scale, dpi_scale)), 1.8)
    return max(
        BASE_FONT_POINT_SIZE,
        round(BASE_FONT_POINT_SIZE * (1 + (scale - 1) * 0.45)),
    )


def qt_alignment(*flags: QtCore.Qt.AlignmentFlag) -> QtCore.Qt.AlignmentFlag:
    value = 0
    for flag in flags:
        value |= int(flag)
    return QtCore.Qt.AlignmentFlag(value)


def parse_event_time_label(value: str) -> datetime:
    if not isinstance(value, str):
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    text = value.strip()
    if not text:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        time_part, meridiem = text.rsplit(" ", 1)
        hour_text, minute_text = time_part.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        meridiem = meridiem.upper()

        if meridiem == "AM":
            hour = 0 if hour == 12 else hour
        elif meridiem == "PM":
            hour = 12 if hour == 12 else hour + 12
        else:
            raise ValueError
    except (TypeError, ValueError):
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return datetime.now().replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


class EventTickTimer(QtCore.QTimer):
    def __init__(self, event: Event):
        super(EventTickTimer, self).__init__()
        self.event_time = parse_event_time_label(event.time)


class TitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(TitleLabel, self).__init__(text)
        self.setFont(build_font(26, QtGui.QFont.Weight.Bold))
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))


class SubtitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(SubtitleLabel, self).__init__(text)
        self.setFont(build_font(16, QtGui.QFont.Weight.Bold))
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))


class HeadingLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(HeadingLabel, self).__init__(text)
        self.setFont(build_font(10, QtGui.QFont.Weight.Bold))
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))


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
        self.setFont(build_font(font_size))
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))
        self.setStyleSheet("background-color: transparent;")


class LargeInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(LargeInfoLabel, self).__init__(data, 14)
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))


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
        if self.max_value == 0:
            self.max_value = 1
        value = int((self.value / self.max_value) * self.width())
        self.setFixedWidth(value)
        self.setStyleSheet("background-color: #00FF00; border-radius: 5;")


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=-1, v_spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._items: list[QtWidgets.QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def __del__(self):
        while self.count():
            self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QtCore.QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def horizontalSpacing(self):
        if self._h_spacing >= 0:
            return self._h_spacing
        return self._smart_spacing(
            QtWidgets.QStyle.PixelMetric.PM_LayoutHorizontalSpacing
        )

    def verticalSpacing(self):
        if self._v_spacing >= 0:
            return self._v_spacing
        return self._smart_spacing(
            QtWidgets.QStyle.PixelMetric.PM_LayoutVerticalSpacing
        )

    def _do_layout(self, rect: QtCore.QRect, test_only: bool):
        margins = self.contentsMargins()
        left = margins.left()
        top = margins.top()
        right = margins.right()
        bottom = margins.bottom()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing_x = max(8, self.horizontalSpacing())
        spacing_y = max(8, self.verticalSpacing())

        for item in self._items:
            next_x = x + item.sizeHint().width() + spacing_x
            if next_x - spacing_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing_y
                next_x = x + item.sizeHint().width() + spacing_x
                line_height = 0

            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom

    def _smart_spacing(self, pixel_metric):
        parent = self.parent()
        if parent is None:
            return 8
        if isinstance(parent, QtWidgets.QWidget):
            return parent.style().pixelMetric(pixel_metric, None, parent)
        return 8


class DetailChip(QtWidgets.QFrame):
    def __init__(
        self,
        title: str,
        value: str,
        tooltip: str = "",
        accent: str = "",
    ):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setObjectName("detailChip")
        self.setStyleSheet(
            "QFrame#detailChip {"
            "background-color: rgba(255, 255, 255, 0.05);"
            "border: 1px solid rgba(255, 255, 255, 0.08);"
            "border-radius: 8px;"
            "}"
        )
        self.setMinimumWidth(112)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        self.setLayout(layout)

        title_label = QtWidgets.QLabel(title.upper())
        title_label.setStyleSheet("color: #9fb0bd; background-color: transparent;")
        title_font = build_font(8)
        title_font.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
        title_label.setFont(title_font)

        value_label = QtWidgets.QLabel(value)
        value_label.setWordWrap(True)
        value_label.setStyleSheet("background-color: transparent;")
        if accent:
            value_label.setStyleSheet(
                f"background-color: transparent; color: {accent}; font-weight: 600;"
            )

        self.value_label = value_label
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        if tooltip:
            self.setToolTip(tooltip)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_tooltip(self, tooltip: str):
        self.setToolTip(tooltip)


def format_price(price: float) -> str:
    if price > 20:
        return f"${price:.0f}"
    return f"${price:.2f}"


def accent_from_score(score: int) -> str:
    if score >= 3:
        return "#d503ff"
    if score == 2:
        return "red"
    if score == 1:
        return "orange"
    return ""


def selection_odds(selection: Selection) -> tuple[float, float]:
    win_prices = [odds.price for odds in selection.odds if odds.bet_type == "Win"]
    place_prices = [odds.price for odds in selection.odds if odds.bet_type == "Place"]
    win_odds = win_prices[0] if win_prices else 0.0
    place_odds = place_prices[0] if place_prices else 0.0
    return win_odds, place_odds


def position_at_distance(run: Run, distance: int) -> int:
    for position_summary in run.position_summaries:
        if (
            position_summary.distance == distance
            and position_summary.position is not None
        ):
            return position_summary.position
    return 0


def format_run_margin(run: Run) -> str:
    if run.margin is None:
        return "-"
    if run.margin == 0.00:
        if run.second_margin is not None:
            return f"+{run.second_margin}"
        return f"{run.margin}"
    return f"{run.margin}"


def format_run_price(run: Run) -> str:
    if run.fluctuation is None or run.fluctuation == 0.00:
        return f"${run.open_price}/${run.starting_price}"
    return f"${run.open_price}/${run.fluctuation}/${run.starting_price}"


def run_sectional_value(run: Run, distance: int) -> Union[str, float]:
    if distance == 800:
        if (
            run.splits.runner_split_l600 is None
            or run.splits.runner_split_l400 is None
            or run.splits.runner_split_l200 is None
            or run.splits.runner_split_finish is None
        ):
            return "-"
        return (
            run.splits.runner_split_l600
            + run.splits.runner_split_l400
            + run.splits.runner_split_l200
            + run.splits.runner_split_finish
        )
    if distance == 600:
        if (
            run.splits.runner_split_l400 is None
            or run.splits.runner_split_l200 is None
            or run.splits.runner_split_finish is None
        ):
            return "-"
        return (
            run.splits.runner_split_l400
            + run.splits.runner_split_l200
            + run.splits.runner_split_finish
        )
    if distance == 400:
        if (
            run.splits.runner_split_l200 is None
            or run.splits.runner_split_finish is None
        ):
            return "-"
        return run.splits.runner_split_l200 + run.splits.runner_split_finish
    if distance == 200:
        if run.splits.runner_split_finish is None:
            return "-"
        return run.splits.runner_split_finish
    return "-"


def format_sectional_display(
    value: Union[str, float, int, None], position: int = 0
) -> str:
    if isinstance(value, (int, float)):
        minutes, seconds = divmod(value, 60)
        if minutes > 0:
            text = f"{minutes:.0f}:{seconds:.2f}"
        else:
            text = f"{seconds:.2f}"
    elif value is None:
        text = "-"
    else:
        text = str(value)
    if position:
        text += f" [{position}]"
    return text


def benchmark_accent(
    benchmark: Optional[float], race_rank: int, meeting_rank: int
) -> str:
    score = 0
    if benchmark is not None and benchmark <= -1.5:
        score += 1
    if race_rank == 1:
        score += 1
    if meeting_rank != 0 and meeting_rank <= 5:
        score += 1
    return accent_from_score(score)


def cleaned_winner_time(run: Run) -> str:
    if run.winner_time is None or len(run.winner_time) == 0:
        return "-"
    winner_time = run.winner_time[:-1]
    if winner_time and winner_time[0] == "0":
        winner_time = winner_time[1:]
    return winner_time


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
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonPress
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
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
        self,
        sectional: Union[str, float],
        benchmark: Optional[float],
        race_rank: int,
        meeting_rank: int,
        position: int,
    ):
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
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonPress
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            label_text = ""
            if self.displaying_benchmark:
                if type(self.sectional) is float:
                    minutes, seconds = divmod(self.sectional, 60)
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
        self.setFont(build_font(10, QtGui.QFont.Weight.Bold))
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

        finish_pos_label = SmallInfoLabel(f"{run.finish_position} of {run.starters}")
        finish_pos_label.setFixedWidth(screen_width_percentage(0.03))

        tooltip = ""
        if run.winner_name is not None:
            tooltip += f"1st: {run.winner_name}"
        if run.second_name is not None:
            tooltip += f"\n2nd: {run.second_name}"
        if run.third_name is not None:
            tooltip += f"\n3rd: {run.third_name}"
        if run.competitors_won_since is not None:
            tooltip += f"\n\n{run.competitors_won_since} Won Since"
        finish_pos_label.setToolTip(tooltip)
        layout.addWidget(finish_pos_label)

        margin_label = SmallInfoLabel(format_run_margin(run))
        margin_label.setFixedWidth(screen_width_percentage(0.021))

        tooltip = ""
        if run.second_margin is not None:
            tooltip += f"2nd Margin: {run.second_margin}"
        if run.third_margin is not None:
            tooltip += f"\n3rd Margin: {run.third_margin}"
        margin_label.setToolTip(tooltip)
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
            price_label = SmallInfoLabel(format_run_price(run))
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
            sectional_specs = [
                (
                    "L800",
                    800,
                    run.form_benchmark.runner_time_difference_l800,
                    run.form_benchmark.runner_race_position_l800,
                    run.form_benchmark.runner_meeting_position_l800,
                ),
                (
                    "L600",
                    600,
                    run.form_benchmark.runner_time_difference_l600,
                    run.form_benchmark.runner_race_position_l600,
                    run.form_benchmark.runner_meeting_position_l600,
                ),
                (
                    "L400",
                    400,
                    run.form_benchmark.runner_time_difference_l400,
                    run.form_benchmark.runner_race_position_l400,
                    run.form_benchmark.runner_meeting_position_l400,
                ),
                (
                    "L200",
                    200,
                    run.form_benchmark.runner_time_difference_l200,
                    run.form_benchmark.runner_race_position_l200,
                    run.form_benchmark.runner_meeting_position_l200,
                ),
            ]
            for label, distance, benchmark, race_rank, meeting_rank in sectional_specs:
                position = position_at_distance(run, distance)
                value = run_sectional_value(run, distance)
                tooltip = ""
                if benchmark is not None:
                    tooltip += f"Benchmark: {benchmark:.1f}"
                if race_rank is not None:
                    tooltip += f"\nRace Rank: {race_rank}"
                if meeting_rank is not None:
                    tooltip += f"\nMeeting Rank: {meeting_rank}"
                sectional_label = SectionalWidget(
                    value,
                    benchmark,
                    race_rank,
                    meeting_rank,
                    position,
                )
                if distance == 200:
                    sectional_label.setFixedWidth(screen_width_percentage(0.025))
                else:
                    sectional_label.setFixedWidth(screen_width_percentage(0.035))
                sectional_label.setToolTip(tooltip)
                layout.addWidget(sectional_label)

            overall_time_label = SectionalWidget(
                run.finish_time,
                run.form_benchmark.runner_time_difference,
                0,
                0,
                run.finish_position,
            )
            overall_time_label.setFixedWidth(screen_width_percentage(0.04))
            layout.addWidget(overall_time_label)

            winner_time_label = SectionalWidget(
                cleaned_winner_time(run),
                run.form_benchmark.winner_time_difference,
                0,
                0,
                0,
            )
            winner_time_label.setFixedWidth(screen_width_percentage(0.03))
            layout.addWidget(winner_time_label)

            runner_tempo_label = TempoWidget(
                run.form_benchmark.runner_tempo_difference,
                run.form_benchmark.runner_tempo_label,
            )
            runner_tempo_label.setFixedWidth(screen_width_percentage(0.03))
            layout.addWidget(runner_tempo_label)

            winner_tempo_label = TempoWidget(
                run.form_benchmark.leader_tempo_difference,
                run.form_benchmark.leader_tempo_label,
            )
            winner_tempo_label.setFixedWidth(screen_width_percentage(0.03))
            layout.addWidget(winner_tempo_label)

            comment_icon = QtGui.QIcon("icons/comment.png")
            comment_icon_label = QtWidgets.QLabel()
            comment_icon_label.setStyleSheet("background-color: transparent;")
            comment_icon_label.setPixmap(
                comment_icon.pixmap(
                    screen_height_percentage(0.02), screen_width_percentage(0.02)
                )
            )
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
        days_since_label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))
        hline_start = QHLine()
        hline_start.setStyleSheet(hline_start.styleSheet() + "border-radius: 2;")
        layout.addWidget(hline_start)
        layout.addWidget(days_since_label)
        hline_end = QHLine()
        hline_end.setStyleSheet(hline_end.styleSheet() + "border-radius: 2;")
        layout.addWidget(hline_end)


class SelectionWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, selection: Selection, venue: str):
        super(SelectionWidget, self).__init__()
        self.selection = selection
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.04); border-radius: 10px;"
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 8, 10, 8)

        name_label = LargeInfoLabel(f"{selection.number}. {selection.name}")
        name_label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))
        name_label.setWordWrap(False)
        name_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(name_label, 1)

        win_odds, place_odds = selection_odds(selection)
        odds_text = f"{format_price(win_odds)} / {format_price(place_odds)}"

        weight_string = f"{selection.weight}kg"
        if selection.claim != 0:
            weight_string += f" (a{selection.claim})"

        speed_position = selection.prediction.normalized_speed_position
        if speed_position is not None:
            speed_position = speed_position.capitalize()

        def ordinal(n):
            return "%d%s" % (
                n,
                "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
            )

        score = 0
        win_percentage, average_difference, std_dev = (
            selection.preparation_stats.get_preparation_stats(
                selection.runs_since_spell
            )
        )
        if win_percentage is not None and win_percentage >= 0.33:
            score += 1
        if average_difference is not None and average_difference <= -1:
            score += 1
        if std_dev is not None and std_dev != 0.00 and std_dev <= 0.5:
            score += 1
        prep_accent = accent_from_score(score)
        tooltip = ""
        if win_percentage is not None:
            tooltip += f"Win Percentage\n{win_percentage * 100:.0f}%"
        if average_difference is not None:
            tooltip += f"\nAverage Difference\n{average_difference:.2f}"
        if std_dev is not None:
            tooltip += f"\nStandard Deviation\n{std_dev:.2f}"

        if selection.days_since_last is None or selection.days_since_last == 0:
            days_since_text = "Unraced"
        else:
            days_since_text = f"{selection.days_since_last} days"

        summary_values = [
            ("Wt", weight_string, "", ""),
            ("Bar", str(selection.barrier), "", ""),
            ("Speed", speed_position or "-", "", ""),
            ("Odds", odds_text, "", ""),
            (
                "ROI",
                f"{selection.roi:.0f}%",
                "",
                "orange" if selection.roi > 0 else "",
            ),
            (
                "Prep",
                f"{ordinal(selection.runs_since_spell + 1)} up",
                tooltip,
                prep_accent,
            ),
            ("Fresh", days_since_text, "", ""),
        ]

        for title, value, label_tooltip, accent in summary_values:
            summary_label = SmallInfoLabel(f"{title}: {value}")
            summary_label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))
            if label_tooltip:
                summary_label.setToolTip(label_tooltip)
            if accent:
                summary_label.setStyleSheet(
                    summary_label.styleSheet() + f"color: {accent};"
                )
            layout.addWidget(summary_label)

        layout.addStretch()
        self.install_click_filters()

    def install_click_filters(self):
        self.installEventFilter(self)
        for child in self.findChildren(QtWidgets.QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonPress
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            self.clicked.emit()
            return True
        elif (
            event.type() == QtCore.QEvent.Type.MouseButtonPress
            and event.button() == QtCore.Qt.MouseButton.RightButton
        ):
            # copy selection name and number to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(
                f"Rx {self.selection.number}. {self.selection.name}: Medium"
            )
        return False


class SelectionDetailsWidget(QtWidgets.QWidget):
    def __init__(self, selection: Selection, venue: str):
        super(SelectionDetailsWidget, self).__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignTop))

        trainer_label_text = "T: " + selection.trainer.name
        if selection.trainer.location is not None:
            match_ratio = SequenceMatcher(
                None, selection.trainer.location, venue
            ).ratio()
            if match_ratio > 0.8:
                trainer_label_text += " [H]"
        trainer_label = SmallInfoLabel(trainer_label_text)
        score = 0
        if (
            selection.trainer.last_year_win_percentage is not None
            and selection.trainer.last_year_win_percentage >= 0.18
        ):
            score += 1
        if (
            selection.trainer_jockey_win_percentage is not None
            and selection.trainer_jockey_win_percentage >= 20
        ):
            score += 1
        if score == 1:
            trainer_label.setStyleSheet(trainer_label.styleSheet() + "color: orange;")
        elif score == 2:
            trainer_label.setStyleSheet(trainer_label.styleSheet() + "color: red;")
        tooltip = ""
        if selection.trainer.last_year_win_percentage is not None:
            tooltip += f"Last Year Win Percentage\n{selection.trainer.last_year_win_percentage * 100:.0f}%"
        if selection.trainer.last_year_place_percentage is not None:
            tooltip += f"\nLast Year Place Percentage\n{selection.trainer.last_year_place_percentage * 100:.0f}%"
        if selection.trainer_jockey_win_percentage is not None:
            tooltip += f"\nTrainer Jockey Win Percentage\n{selection.trainer_jockey_win_percentage:.0f}%"
        trainer_label.setToolTip(tooltip)

        jockey_label = SmallInfoLabel("J: " + selection.jockey.name)
        score = 0
        if (
            selection.jockey.last_year_win_percentage is not None
            and selection.jockey.last_year_win_percentage >= 0.14
        ):
            score += 1
        if (
            selection.trainer_jockey_win_percentage is not None
            and selection.trainer_jockey_win_percentage >= 20
        ):
            score += 1
        if score == 1:
            jockey_label.setStyleSheet(jockey_label.styleSheet() + "color: orange;")
        elif score == 2:
            jockey_label.setStyleSheet(jockey_label.styleSheet() + "color: red;")
        tooltip = ""
        if selection.jockey.last_year_win_percentage is not None:
            tooltip += f"Last Year Win Percentage\n{selection.jockey.last_year_win_percentage * 100:.0f}%"
        if selection.jockey.last_year_place_percentage is not None:
            tooltip += f"\nLast Year Place Percentage\n{selection.jockey.last_year_place_percentage * 100:.0f}%"
        if selection.trainer_jockey_win_percentage is not None:
            tooltip += f"\nTrainer Jockey Win Percentage\n{selection.trainer_jockey_win_percentage:.0f}%"
        jockey_label.setToolTip(tooltip)

        people_layout = QtWidgets.QHBoxLayout()
        people_layout.setContentsMargins(0, 0, 0, 0)
        people_layout.setSpacing(12)
        trainer_label.setWordWrap(True)
        jockey_label.setWordWrap(True)
        people_layout.addWidget(trainer_label, 1)
        people_layout.addWidget(jockey_label, 1)
        layout.addLayout(people_layout)

        speed_position = selection.prediction.normalized_speed_position
        if speed_position is not None:
            speed_position = speed_position.capitalize()

        weight_string = f"{selection.weight}kg"
        if selection.claim != 0:
            weight_string += f" (a{selection.claim})"

        def ordinal(n):
            return "%d%s" % (
                n,
                "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
            )

        score = 0
        win_percentage, average_difference, std_dev = (
            selection.preparation_stats.get_preparation_stats(
                selection.runs_since_spell
            )
        )
        if win_percentage is not None and win_percentage >= 0.33:
            score += 1
        if average_difference is not None and average_difference <= -1:
            score += 1
        if std_dev is not None and std_dev != 0.00 and std_dev <= 0.5:
            score += 1
        prep_accent = accent_from_score(score)
        tooltip = ""
        if win_percentage is not None:
            tooltip += f"Win Percentage\n{win_percentage * 100:.0f}%"
        if average_difference is not None:
            tooltip += f"\nAverage Difference\n{average_difference:.2f}"
        if std_dev is not None:
            tooltip += f"\nStandard Deviation\n{std_dev:.2f}"

        if selection.days_since_last is None or selection.days_since_last == 0:
            days_since_text = "Unraced"
        else:
            days_since_text = f"{selection.days_since_last} days"

        win_odds, place_odds = selection_odds(selection)
        odds_text = f"{format_price(win_odds)} / {format_price(place_odds)}"

        chip_container = QtWidgets.QWidget()
        chip_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        chip_layout = FlowLayout()
        chip_container.setLayout(chip_layout)
        chip_layout.addWidget(
            DetailChip(
                "Record",
                f"{selection.total_runs}:{selection.total_wins}-{selection.total_places}",
            )
        )
        chip_layout.addWidget(DetailChip("Weight", weight_string))
        chip_layout.addWidget(DetailChip("Barrier", str(selection.barrier)))
        chip_layout.addWidget(DetailChip("Speed", speed_position or "-"))
        chip_layout.addWidget(DetailChip("Odds", odds_text))
        chip_layout.addWidget(
            DetailChip(
                "ROI",
                f"{selection.roi:.0f}%",
                accent="orange" if selection.roi > 0 else "",
            )
        )
        chip_layout.addWidget(
            DetailChip(
                "Prep",
                f"{ordinal(selection.runs_since_spell + 1)} up",
                tooltip,
                prep_accent,
            )
        )
        chip_layout.addWidget(DetailChip("Freshness", days_since_text))
        trainer_jockey_percentage = selection.trainer_jockey_win_percentage
        chip_layout.addWidget(
            DetailChip(
                "T/J Win",
                (
                    f"{trainer_jockey_percentage:.0f}%"
                    if trainer_jockey_percentage is not None
                    else "-"
                ),
                accent=(
                    "red"
                    if trainer_jockey_percentage is not None
                    and trainer_jockey_percentage >= 20
                    else ""
                ),
            )
        )
        punters_edge = selection.punters_edge
        chip_layout.addWidget(
            DetailChip(
                "Edge",
                f"{punters_edge:.2f}" if punters_edge is not None else "-",
                accent=(
                    "orange" if punters_edge is not None and punters_edge > 0 else ""
                ),
            )
        )

        tooltip = ""
        if selection.comments is not None:
            tooltip += f"General Comments\n{selection.comments}"
        for brand, comment in selection.external_comments.items():
            tooltip += f"\n\n{brand.capitalize()}\n{comment}"
        if tooltip:
            chip_layout.addWidget(DetailChip("Comments", "Available", tooltip))
        if selection.gear_changes is None or selection.gear_changes == "":
            gear_tooltip = "No Gear Changes"
            gear_text = "None"
        else:
            gear_tooltip = selection.gear_changes
            gear_text = "Updated"
        chip_layout.addWidget(DetailChip("Gear", gear_text, gear_tooltip))

        layout.addWidget(chip_container)


class SelectionsWidget(QtWidgets.QWidget):
    def __init__(self, selections: list[Selection], venue: str):
        super(SelectionsWidget, self).__init__()
        self.venue = venue
        self._section_state: dict[int, tuple[Selection, QtWidgets.QTreeWidgetItem]] = {}
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(max(320, screen_height_percentage(0.35)))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContentsMargins(0, 0, 0, 0)
        self.tree.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.tree.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.setIndentation(0)

        self.define_sections(selections, venue)

    def define_sections(self, selections: list[Selection], venue: str):
        for selection in selections:
            button = self.add_button(selection, venue)
            section = self.add_widget(button)
            button.addChild(section)
            self._section_state[id(button)] = (selection, section)

    def build_section_widget(self, selection: Selection) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(self.tree)
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout = QtWidgets.QVBoxLayout(widget)
        widget.setLayout(layout)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(8)
        layout.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignTop))

        layout.addWidget(SelectionDetailsWidget(selection, self.venue))

        if selection.runs:
            layout.addWidget(RunsTitleWidget())

        to_date = datetime.now()
        for run in selection.runs[:10]:
            from_date = datetime.strptime(run.meeting_date, "%Y-%m-%d")
            if (to_date - from_date).days > (SPELL_THRESHOLD - 20):
                layout.addWidget(SpellWidget((to_date - from_date).days))
            to_date = from_date
            layout.addWidget(RunsWidget(run, selection.weight - selection.claim))
        return widget

    def add_button(self, selection: Selection, venue: str):
        item = QtWidgets.QTreeWidgetItem()
        count = self.tree.topLevelItemCount()
        if count % 2 == 0:
            item.setBackground(0, QtGui.QColor(84, 104, 122))
        else:
            item.setBackground(0, QtGui.QColor(74, 94, 112))
        self.tree.addTopLevelItem(item)
        expand_button = SelectionWidget(selection, venue)
        expand_button.clicked.connect(lambda item=item: self.on_clicked(item))
        self.tree.setItemWidget(item, 0, expand_button)
        item.setSizeHint(0, expand_button.sizeHint())
        return item

    def on_clicked(self, item):
        section_state = self._section_state.get(id(item))
        if section_state is not None:
            selection, section = section_state
            if self.tree.itemWidget(section, 0) is None:
                section_widget = self.build_section_widget(selection)
                self.tree.setItemWidget(section, 0, section_widget)
                section.setSizeHint(0, section_widget.sizeHint())
        if item.isExpanded():
            item.setExpanded(False)
        else:
            item.setExpanded(True)

    def add_widget(self, button):
        section = QtWidgets.QTreeWidgetItem(button)
        section.setDisabled(True)
        return section


class EventInfoWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventInfoWidget, self).__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(8)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        title_label = SubtitleLabel(event.name)
        title_label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)
        header_layout.addWidget(SmallInfoLabel(event.time))
        layout.addLayout(header_layout)

        chips_widget = QtWidgets.QWidget()
        chips_layout = FlowLayout()
        chips_widget.setLayout(chips_layout)

        pace_text = (
            f"{round(event.pace, 2)} Pace Rating"
            if event.pace is not None
            else "Unknown"
        )
        self.time_remaining_chip = DetailChip(
            "Countdown",
            self.get_time_remaining(parse_event_time_label(event.time)),
        )
        chips_layout.addWidget(self.time_remaining_chip)
        chips_layout.addWidget(DetailChip("Distance", f"{event.distance}m"))
        chips_layout.addWidget(DetailChip("Prize", f"${event.prize_money:,}"))
        chips_layout.addWidget(DetailChip("Pace", pace_text))
        chips_layout.addWidget(DetailChip("Starters", f"{event.starters} Runners"))
        full_class_text = f"{event._class} Class"
        class_chip = DetailChip(
            "Class",
            shorten(full_class_text, width=32, placeholder="..."),
            full_class_text,
        )
        class_chip.setMinimumWidth(max(170, screen_width_percentage(0.12)))
        class_chip.value_label.setWordWrap(False)
        chips_layout.addWidget(class_chip)
        layout.addWidget(chips_widget)

        self.tick_timer = EventTickTimer(event)
        self.tick_timer.timeout.connect(self.update_time_remaining)
        self.tick_timer.start(1000)

    def get_time_remaining(self, event_time: datetime) -> str:
        current_time = datetime.now()
        event_time = event_time.replace(
            year=current_time.year, month=current_time.month, day=current_time.day
        )
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
        self.time_remaining_chip.set_value(
            self.get_time_remaining(self.tick_timer.event_time)
        )
        self.tick_timer.start(1000)


class EventWidget(QtWidgets.QWidget):
    def __init__(self, event: Event, venue: str):
        super(EventWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(EventInfoWidget(event), 0)
        layout.addWidget(SelectionsWidget(event.selections, venue), 1)


class DeferredContentPlaceholder(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(DeferredContentPlaceholder, self).__init__(text)
        self.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))
        self.setStyleSheet("color: #9fb0bd; background-color: transparent;")


class EventsTabWidget(QtWidgets.QTabWidget):
    def __init__(self, meeting: Meeting):
        super(EventsTabWidget, self).__init__()
        self.meeting = meeting
        self._loaded_tabs: set[int] = set()
        self.tabBar().hide()
        self.setContentsMargins(0, 0, 0, 0)
        for event in meeting.events:
            self.addTab(DeferredContentPlaceholder("Loading event..."), event.name)
        self.currentChanged.connect(self.ensure_tab_loaded)
        QtCore.QTimer.singleShot(0, lambda: self.ensure_tab_loaded(0))

    def ensure_tab_loaded(self, index: int):
        if index < 0 or index >= len(self.meeting.events):
            return
        if index in self._loaded_tabs:
            return
        placeholder = self.widget(index)
        event_widget = EventWidget(self.meeting.events[index], self.meeting.name)
        self.removeTab(index)
        self.insertTab(index, event_widget, self.meeting.events[index].name)
        if placeholder is not None:
            placeholder.deleteLater()
        self._loaded_tabs.add(index)
        self.setCurrentIndex(index)


class EventNumberWidget(QtWidgets.QWidget):
    selected = QtCore.Signal(int)

    def __init__(self, event: Event):
        super(EventNumberWidget, self).__init__()

        self.event_index = event.event_number - 1
        event_layout = QtWidgets.QVBoxLayout()
        self.setLayout(event_layout)
        event_layout.setContentsMargins(0, 0, 0, 0)
        event_layout.setSpacing(4)
        self.event_button = QtWidgets.QPushButton(f"{event.event_number}")
        self.event_button.setFont(build_font(16, QtGui.QFont.Weight.Bold))
        self.event_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.event_button.setStyleSheet("border-radius: 5;")
        self.event_button.setMinimumWidth(max(48, screen_width_percentage(0.032)))
        self.event_button.setMinimumHeight(max(38, screen_height_percentage(0.035)))
        self.event_button.clicked.connect(self.button_clicked)
        event_label = LargeInfoLabel(f"{event.time}")
        event_layout.addWidget(
            self.event_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        event_layout.addWidget(event_label)
        event_layout.addStretch()

    def button_clicked(self):
        self.selected.emit(self.event_index)

    def set_active(self, active: bool):
        if active:
            self.setStyleSheet("background-color: #303c46;")
            self.event_button.setStyleSheet(
                "border-radius: 5; background-color: #435464;"
            )
            return
        self.setStyleSheet("background-color: #54687a;")
        self.event_button.setStyleSheet("border-radius: 5;")


class EventNumbersWidget(QtWidgets.QWidget):
    eventSelected = QtCore.Signal(int)

    def __init__(self, meeting: Meeting):
        super(EventNumbersWidget, self).__init__()

        self._current_index = 0
        self._event_widgets: list[EventNumberWidget] = []
        events_layout = QtWidgets.QHBoxLayout()
        self.setLayout(events_layout)
        events_layout.setContentsMargins(0, 0, 0, 0)
        events_layout.setSpacing(8)
        for event in meeting.events:
            event_widget = EventNumberWidget(event)
            event_widget.selected.connect(self.set_current_index)
            self._event_widgets.append(event_widget)
            events_layout.addWidget(event_widget)
        events_layout.addStretch()
        if self._event_widgets:
            self.set_current_index(0, emit_signal=False)

    def set_current_index(self, index: int, emit_signal: bool = True):
        if not self._event_widgets:
            return
        self._current_index = max(0, min(index, len(self._event_widgets) - 1))
        for widget_index, widget in enumerate(self._event_widgets):
            widget.set_active(widget_index == self._current_index)
        if emit_signal:
            self.eventSelected.emit(self._current_index)


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
        layout.addWidget(
            HorizontalBar(value, max_value), alignment=QtCore.Qt.AlignmentFlag.AlignLeft
        )
        if value > 1000:
            layout.addWidget(VerySmallInfoLabel(numerize.numerize(value, 1)))
        else:
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
            event.selections,
            key=lambda x: x.trainer_jockey_win_percentage,
            reverse=True,
        )
        selections = selections[:9]
        for selection in selections:
            value = selection.trainer_jockey_win_percentage
            layout.addWidget(
                SelectionGraphWidget(value, 70, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Avg. Prize Money"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            event.selections, key=lambda x: x.average_prize_money, reverse=True
        )
        selections = selections[:9]
        max_value = max([x.average_prize_money for x in selections]) * 1.1
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.average_prize_money
            if value is None:
                value = 0.0
            layout.addWidget(
                SelectionGraphWidget(value, max_value, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Wet W/P %"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        weighted_wet_win_place_values = []
        for selection in event.selections:
            weighted_wet_win_place = (
                (selection.wet_runs_win_percentage or 0.0) * 2
                + (selection.wet_runs_place_percentage or 0.0)
            ) / 3
            weighted_wet_win_place_values.append(
                (selection.number, weighted_wet_win_place)
            )
        weighted_wet_win_place_values.sort(key=lambda x: x[1], reverse=True)
        weighted_wet_win_place_values = weighted_wet_win_place_values[:9]
        # graph based on barrier and predicted speed values
        for wet_win_place in weighted_wet_win_place_values:
            layout.addWidget(
                SelectionGraphWidget(wet_win_place[1], 100, wet_win_place[0]),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )


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
        selections = sorted(event.selections, key=lambda x: int(x.barrier))
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = selection.prediction.normalized_speed
            layout.addWidget(
                SelectionGraphWidget(value, 1.0, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )

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
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )


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
        selections = sorted(
            event.selections,
            key=lambda x: x.punters_edge if x.punters_edge is not None else 0.0,
            reverse=True,
        )[:9]
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = (
                selection.punters_edge if selection.punters_edge is not None else 0.0
            )
            layout.addWidget(
                SelectionGraphWidget(value, 1.0, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )

        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 10))
        layout.addWidget(SubtitleLabel("Predictor"))
        layout.addWidget(QHLine())
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        selections = sorted(
            event.selections,
            key=lambda x: x.predictor_score if x.predictor_score is not None else 0.0,
            reverse=True,
        )[:9]
        max_value = max(
            [
                x.predictor_score if x.predictor_score is not None else 0.0
                for x in selections
            ],
            default=0.0,
        )
        # graph based on barrier and predicted speed values
        for selection in selections:
            value = (
                selection.predictor_score
                if selection.predictor_score is not None
                else 0.0
            )
            layout.addWidget(
                SelectionGraphWidget(value, max_value, selection.number),
                alignment=QtCore.Qt.AlignmentFlag.AlignTop,
            )


ANALYSIS_VIEWS = [
    ("model", "Predictor Analysis", EventModelWidget),
    ("speed", "Speed Analysis", EventSpeedWidget),
    ("stats", "Stats Analysis", EventStatsWidget),
]


class EventAnalysisWidget(QtWidgets.QWidget):
    def __init__(self, event: Event, app_state: AppState):
        super(EventAnalysisWidget, self).__init__()

        self.app_state = app_state
        self.current_event = event
        self._view_cache: dict[str, QtWidgets.QWidget] = {}
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setMinimumWidth(max(260, screen_width_percentage(0.12)))
        self.setMaximumWidth(max(320, screen_width_percentage(0.18)))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignTop))
        self.combo_box = QtWidgets.QComboBox()
        for view_id, label, _ in ANALYSIS_VIEWS:
            self.combo_box.addItem(label, userData=view_id)
        self.combo_box.currentIndexChanged.connect(self.change_analysis)
        layout.addWidget(self.combo_box)
        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.placeholder = DeferredContentPlaceholder("Loading analysis...")
        self.stack.addWidget(self.placeholder)
        self.stack.setCurrentWidget(self.placeholder)
        self.app_state.analysisViewChanged.connect(self.set_analysis_view)
        self.set_analysis_view(self.app_state.analysis_view_id)
        QtCore.QTimer.singleShot(0, lambda event=event: self.set_event(event))

    def set_event(self, event: Event):
        self.current_event = event
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            if widget is None:
                break
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self.placeholder = DeferredContentPlaceholder("Loading analysis...")
        self.stack.addWidget(self.placeholder)
        self.stack.setCurrentWidget(self.placeholder)
        self._view_cache.clear()
        QtCore.QTimer.singleShot(0, lambda: self.show_analysis(self.current_view_id()))

    def current_view_id(self) -> str:
        view_id = self.combo_box.currentData()
        if isinstance(view_id, str):
            return view_id
        return ANALYSIS_VIEWS[0][0]

    def show_analysis(self, view_id: str):
        if view_id not in self._view_cache:
            for registered_view_id, _, factory in ANALYSIS_VIEWS:
                if registered_view_id != view_id:
                    continue
                widget = factory(self.current_event)
                self._view_cache[view_id] = widget
                self.stack.addWidget(widget)
                break
        current_widget = self._view_cache.get(view_id)
        if current_widget is not None:
            self.stack.setCurrentWidget(current_widget)

    def change_analysis(self, _index: int):
        view_id = self.current_view_id()
        self.show_analysis(view_id)
        self.app_state.set_analysis_view(view_id)

    def set_analysis_view(self, view_id: str):
        index = self.combo_box.findData(view_id)
        if index == -1:
            return
        if self.combo_box.currentIndex() != index:
            self.combo_box.setCurrentIndex(index)
            return
        self.show_analysis(view_id)


class EventsInfoWidget(QtWidgets.QWidget):
    eventSelected = QtCore.Signal(int)

    def __init__(self, meeting: Meeting):
        super(EventsInfoWidget, self).__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.event_numbers_widget = EventNumbersWidget(meeting)
        numbers_scroll_area = QtWidgets.QScrollArea()
        numbers_scroll_area.setWidgetResizable(True)
        numbers_scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        numbers_scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        numbers_scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        numbers_scroll_area.setWidget(self.event_numbers_widget)
        layout.addWidget(
            numbers_scroll_area, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )
        self.event_tab_widget = EventsTabWidget(meeting)
        layout.addWidget(self.event_tab_widget, 1)
        self.event_numbers_widget.eventSelected.connect(self.set_tab_index)

    def set_tab_index(self, index: int):
        self.event_tab_widget.setCurrentIndex(index)
        self.eventSelected.emit(index)


class EventsWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting, app_state: AppState):
        super(EventsWidget, self).__init__()

        self.meeting = meeting
        self.app_state = app_state
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.events_info_widget = EventsInfoWidget(self.meeting)
        self.analysis_widget = EventAnalysisWidget(
            self.meeting.events[0], self.app_state
        )
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.events_info_widget)
        self.splitter.addWidget(self.analysis_widget)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter)
        self.events_info_widget.eventSelected.connect(self.change_race)
        self.update_splitter_orientation()

    def change_race(self, event_number: int):
        if event_number < 0 or event_number >= len(self.meeting.events):
            return
        self.analysis_widget.set_event(self.meeting.events[event_number])

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.update_splitter_orientation()

    def update_splitter_orientation(self):
        if self.width() < 1300:
            self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
            return
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)


class MeetingInfoWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(MeetingInfoWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setMinimumWidth(max(220, screen_width_percentage(0.1)))
        self.setMaximumWidth(max(260, screen_width_percentage(0.18)))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        layout.addWidget(SubtitleLabel("Track"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(meeting.name))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel("Rail Position"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(meeting.rail_position))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        track_condition = meeting.events[0].track_condition
        track_type = meeting.events[0].track_type
        weather = meeting.events[0].weather

        layout.addWidget(SubtitleLabel("Condition"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(track_condition))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel("Track Type"))
        layout.addWidget(QHLine())
        layout.addWidget(LargeInfoLabel(track_type))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))

        layout.addWidget(SubtitleLabel("Weather"))
        layout.addWidget(QHLine())
        if weather is None:
            weather = "Unknown"
        layout.addWidget(LargeInfoLabel(weather.capitalize()))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 15))
        layout.addStretch()


class MeetingsTab(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting, app_state: AppState):
        super(MeetingsTab, self).__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        meeting_info_widget = MeetingInfoWidget(meeting)
        events_widget = EventsWidget(meeting, app_state)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(meeting_info_widget)
        self.splitter.addWidget(events_widget)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 5)
        layout.addWidget(self.splitter)
        self.update_splitter_orientation()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.update_splitter_orientation()

    def update_splitter_orientation(self):
        if self.width() < 1180:
            self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
            return
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)


class DeferredMeetingTab(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting, app_state: AppState):
        super(DeferredMeetingTab, self).__init__()
        self.meeting = meeting
        self.app_state = app_state
        self._loaded = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.placeholder = DeferredContentPlaceholder("Loading meeting...")
        layout.addWidget(self.placeholder)
        QtCore.QTimer.singleShot(0, self.load_content)

    @QtCore.Slot()
    def load_content(self):
        if self._loaded:
            return

        layout = self.layout()
        if layout is None:
            return

        meeting_tab = MeetingsTab(self.meeting, self.app_state)
        layout.removeWidget(self.placeholder)
        self.placeholder.deleteLater()
        layout.addWidget(meeting_tab)
        self._loaded = True


class ScraperTab(QtWidgets.QScrollArea):
    def __init__(self, scraper: MeetingsScraper, app_state: AppState):
        super(ScraperTab, self).__init__()

        self.scraper = scraper
        self.app_state = app_state
        self.worker_thread: Optional[QtCore.QThread] = None
        self.worker: Optional[MeetingsLoadWorker] = None
        main_widget = QtWidgets.QWidget()
        self.setStyleSheet("QScrollArea {border: 0px;}")
        self.setLayout(QtWidgets.QFormLayout())
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)
        self.setWidgetResizable(True)

        date_widget = QtWidgets.QWidget()
        date_widget.setMinimumWidth(max(220, screen_width_percentage(0.12)))
        date_widget.setMaximumWidth(max(300, screen_width_percentage(0.2)))
        date_form = QtWidgets.QFormLayout()
        date_widget.setLayout(date_form)
        label = LargeInfoLabel("Date to Scrape")
        font = build_font(16, QtGui.QFont.Weight.Bold)
        font.setUnderline(True)
        label.setFont(font)

        label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignCenter))
        date_form.addRow(label)
        self.date_selector = QtWidgets.QDateEdit()
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setDate(QtCore.QDate.currentDate())
        date_form.addWidget(self.date_selector)
        self.scrape_button = QtWidgets.QPushButton("Extract")
        date_form.addWidget(self.scrape_button)
        self.scrape_button.clicked.connect(
            lambda: self.scrape_date(self.date_selector.date())
        )
        self.local_checkbox = QtWidgets.QCheckBox("Use local data")
        self.local_checkbox.setChecked(True)
        date_form.addWidget(self.local_checkbox)
        self.status_label = SmallInfoLabel("Choose a date and extract meetings.")
        self.status_label.setWordWrap(True)
        date_form.addWidget(self.status_label)

        meetings_widget = QtWidgets.QScrollArea()
        meetings_widget.setWidgetResizable(True)
        meetings_group = QtWidgets.QGroupBox()
        meetings_widget.setWidget(meetings_group)
        meetings_widget.setStyleSheet("QGroupBox {border: 0px;}")
        self.meetings_form = QtWidgets.QFormLayout()
        meetings_group.setLayout(self.meetings_form)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(date_widget)
        self.splitter.addWidget(meetings_widget)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        main_layout.addWidget(self.splitter)
        self.update_splitter_orientation()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.update_splitter_orientation()

    def update_splitter_orientation(self):
        if self.width() < 980:
            self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
            return
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)

    def scrape_date(self, date: QtCore.QDate):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            return

        parent = self.parent()
        tab_widget = parent.parent() if parent is not None else None
        if isinstance(tab_widget, QtWidgets.QTabWidget):
            tabs = cast(QtWidgets.QTabWidget, tab_widget)
            for i in reversed(range(tabs.count())):
                if tabs.tabText(i) != "Home":
                    tabs.removeTab(i)

        for i in reversed(range(self.meetings_form.count())):
            item = self.meetings_form.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, QtWidgets.QWidget):
                widget.setParent(None)
        self.scrape_button.setEnabled(False)
        self.scrape_button.setText("Extracting...")
        self.status_label.setText("Loading meetings...")
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.update()
        self.app_state.set_error("")
        self.app_state.set_loading(True)

        scrape_date = datetime(date.year(), date.month(), date.day())
        worker_thread = QtCore.QThread(self)
        worker = MeetingsLoadWorker(
            scraper=self.scraper,
            scrape_date=scrape_date,
            use_local_data=self.local_checkbox.isChecked(),
        )
        self.worker_thread = worker_thread
        self.worker = worker
        worker.moveToThread(worker_thread)
        worker_thread.started.connect(worker.run)
        worker.finished.connect(self.on_meetings_loaded)
        worker.failed.connect(self.on_meetings_failed)
        worker.finished.connect(worker_thread.quit)
        worker.failed.connect(worker_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker_thread.finished.connect(worker_thread.deleteLater)
        worker_thread.finished.connect(self.on_worker_finished)
        worker_thread.start()

    def on_meetings_loaded(self, meetings: list[Meeting]):
        self.app_state.set_meetings(meetings)
        state_dict = group_by_state(meetings)
        for state, state_meetings in state_dict.items():
            state_frame = self.create_state_frame(state, state_meetings)
            self.meetings_form.addWidget(state_frame)
        if meetings:
            self.status_label.setText(
                f"Loaded {len(meetings)} meeting{'s' if len(meetings) != 1 else ''}."
            )
        else:
            self.status_label.setText("No meetings found for the selected date.")
        self.finish_scrape()

    def on_meetings_failed(self, message: str):
        self.app_state.set_error(message)
        self.status_label.setText(f"Failed to load meetings: {message}")
        QtWidgets.QMessageBox.critical(self, "Load Failed", message)
        self.finish_scrape()

    def finish_scrape(self):
        self.app_state.set_loading(False)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.scrape_button.setText("Extract")
        self.scrape_button.setEnabled(True)

    def on_worker_finished(self):
        self.worker_thread = None
        self.worker = None

    def create_state_frame(
        self, state: str, meetings: list[Meeting]
    ) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout()
        frame.setLayout(layout)
        title_label = TitleLabel(state)
        title_label.setAlignment(qt_alignment(QtCore.Qt.AlignmentFlag.AlignLeft))
        layout.addWidget(title_label)
        layout.addWidget(QHLine())
        state_widget = QtWidgets.QWidget()
        horizontal_layout = QtWidgets.QHBoxLayout()
        state_widget.setLayout(horizontal_layout)
        for meeting in meetings:
            button = QtWidgets.QPushButton(meeting.name)
            button.setProperty("meeting_key", meeting_key(meeting))
            button.setMinimumWidth(max(140, screen_width_percentage(0.08)))
            button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            button.clicked.connect(self.open_meeting_window)
            button.setMinimumHeight(max(36, screen_height_percentage(0.035)))
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
        meeting_id = sender.property("meeting_key")
        if isinstance(meeting_id, str):
            self.app_state.set_selected_meeting(meeting_id)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        sender.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, scraper: MeetingsScraper, app_state: AppState):
        super(MainWindow, self).__init__()

        self.app_state = app_state
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.setContentsMargins(10, 10, 10, 10)
        self.tab_widget.addTab(ScraperTab(scraper, app_state), "Home")
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet("QTabWidget::pane {border: 0;}")
        self.app_state.selectedMeetingChanged.connect(self.open_meeting_tab)

    def close_tab(self, index: int):
        if index == 0:
            return
        self.tab_widget.removeTab(index)

    def open_meeting_tab(self, meeting: Meeting):
        key = meeting_key(meeting)
        for index in range(self.tab_widget.count()):
            if self.tab_widget.tabBar().tabData(index) == key:
                self.tab_widget.setCurrentIndex(index)
                return
        index = self.tab_widget.addTab(
            DeferredMeetingTab(meeting, self.app_state), meeting.name
        )
        self.tab_widget.tabBar().setTabData(index, key)
        self.tab_widget.setCurrentIndex(index)


class MeetingScraperApp(QtWidgets.QApplication):
    def __init__(self):
        super(MeetingScraperApp, self).__init__(sys.argv)

        self.app_state = AppState()
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
        self.setApplicationName("Meeting Scraper")
        self.setApplicationDisplayName("Meeting Scraper")

        app_font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.GeneralFont
        )
        app_font.setPointSize(max(app_font.pointSize(), 12))
        global FONT
        FONT = app_font.family()
        self.setFont(app_font)

    def run(self, scraper: MeetingsScraper) -> int:
        global SCREEN_SIZE
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            SCREEN_SIZE = QtCore.QSize(1600, 900)
        else:
            SCREEN_SIZE = screen.availableGeometry().size()
        app_font = self.font()
        app_font.setPointSize(monitor_font_point_size(screen))
        self.setFont(app_font)
        window = MainWindow(scraper, self.app_state)
        window.setMinimumSize(1100, 720)
        window.showMaximized()

        return self.exec_()
