from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from meetings_data import Meeting, group_by_state, Event, Selection, Run, PositionSummary, FormBenchmark, Trainer, \
    Jockey, Prediction
from scraper import MeetingsScraper
from datetime import datetime
import qdarkstyle
import sys
from typing import Union
from numerize import numerize


class TitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(TitleLabel, self).__init__(text)
        self.setStyleSheet("font-size: 30px; font-weight: bold;")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class SubtitleLabel(QtWidgets.QLabel):
    def __init__(self, text: str):
        super(SubtitleLabel, self).__init__(text)
        self.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


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
        self.setStyleSheet(f"font-size: {font_size}px;")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)


class LargeInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(LargeInfoLabel, self).__init__(data, 18)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class SmallInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(SmallInfoLabel, self).__init__(data, 14)


class VerySmallInfoLabel(InfoLabel):
    def __init__(self, data: Union[str, int, float, object]):
        super(VerySmallInfoLabel, self).__init__(data, 12)


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
        self.max_value = max_value
        self.setFixedHeight(20)
        self.setFixedWidth(140)
        value = int((self.value / self.max_value) * self.width())
        self.setFixedWidth(value)
        self.setStyleSheet(
            f"background-color: #00FF00; border-radius: 5px;")


class SelectionSummaryWidget(QtWidgets.QWidget):
    def __init__(self, selection: Selection):
        super(SelectionSummaryWidget, self).__init__()
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(SmallInfoLabel(selection.number))
        layout.addWidget(SmallInfoLabel(selection.name))
        layout.addWidget(SmallInfoLabel(selection.trainer.name))
        layout.addWidget(SmallInfoLabel(selection.jockey.name))
        layout.addWidget(SmallInfoLabel(selection.weight))
        layout.addWidget(SmallInfoLabel(selection.punters_edge))


class SelectionWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, selection: Selection):
        super(SelectionWidget, self).__init__()
        self.selection = selection
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        selection_summary = SelectionSummaryWidget(selection)
        layout.addWidget(
            selection_summary,
            alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        selection_summary.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and \
                event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
            return True
        return False


class SelectionsWidget(QtWidgets.QWidget):
    def __init__(self, selections: list[Selection]):
        super(SelectionsWidget, self).__init__()

        self.set_size()
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.setIndentation(0)

        self.sections: list[tuple[Selection, QtWidgets.QFrame]] = []
        self.define_sections(selections)
        self.add_sections()

    def set_size(self):
        screen_size = QtWidgets.QApplication.primaryScreen().size()
        self.setFixedHeight(screen_size.height() * 0.7)

    def add_sections(self):
        for (selection, widget) in self.sections:
            button1 = self.add_button(selection)
            section1 = self.add_widget(button1, widget)
            button1.addChild(section1)

    def define_sections(self, selections: list[Selection]):
        for selection in selections:
            widget = QtWidgets.QFrame(self.tree)
            layout = QtWidgets.QHBoxLayout(widget)
            layout.addWidget(QtWidgets.QLabel("Bla"))
            layout.addWidget(QtWidgets.QLabel("Blubb"))
            self.sections.append((selection, widget))

    def add_button(self, selection: Selection):
        item = QtWidgets.QTreeWidgetItem()
        self.tree.addTopLevelItem(item)
        expand_button = SelectionWidget(selection)
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
        layout.addWidget(SmallInfoLabel(self.get_time_remaining(event)))
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

    def get_time_remaining(self, event: Event) -> str:
        current_time = datetime.now()
        event_time = datetime.strptime(event.time, "%I:%M %p")
        timedelta_remaining = event_time - current_time
        # get time remaining in minutes and seconds
        time_remaining = f"{timedelta_remaining.seconds // 60}m {timedelta_remaining.seconds % 60}s"
        return time_remaining


class EventWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(EventInfoWidget(event), 0)
        layout.addWidget(
            SelectionsWidget(event.selections), 1,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop)


class EventsTabWidget(QtWidgets.QTabWidget):
    def __init__(self, meeting: Meeting):
        super(EventsTabWidget, self).__init__()
        self.tabBar().hide()
        self.setContentsMargins(0, 0, 0, 0)
        for event in meeting.events:
            event_widget = EventWidget(event)
            self.addTab(event_widget, event.name)


class EventNumberWidget(QtWidgets.QWidget):
    def __init__(self, event: Event):
        super(EventNumberWidget, self).__init__()

        self.event_number = event.event_number
        event_layout = QtWidgets.QVBoxLayout()
        self.setLayout(event_layout)
        event_button = QtWidgets.QPushButton(
            f"{self.event_number}")
        event_button.setStyleSheet("font-size: 20px; font-weight: bold;")
        event_button.setCursor(QtGui.QCursor(
            QtCore.Qt.CursorShape.PointingHandCursor))
        # make button circular
        event_button.setStyleSheet(
            "border-radius: 20px;")
        event_button.setFixedWidth(40)
        event_button.setFixedHeight(40)
        event_button.clicked.connect(self.button_clicked)
        event_label = LargeInfoLabel(f"{event.time}")
        event_layout.addWidget(
            event_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        event_layout.addWidget(event_label)
        event_layout.addStretch()

    def button_clicked(self):
        event_parent = self.parent()
        if event_parent is None:
            return
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
            events_layout.addWidget(event_widget)
        events_layout.addStretch()


class SelectionGraphWidget(QtWidgets.QWidget):
    def __init__(self, value: float, max_value: float, number: int):
        super(SelectionGraphWidget, self).__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = SmallInfoLabel(number)
        # set width so all labels are the same size
        label.setFixedWidth(25)
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
                SelectionGraphWidget(value, 100, selection.number),
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
        for weighted_wet_win_place in weighted_wet_win_place_values:
            value = weighted_wet_win_place
            if value is None:
                value = 0.0
            layout.addWidget(
                SelectionGraphWidget(
                    weighted_wet_win_place[1],
                    100, weighted_wet_win_place[0]),
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
        max_value = max([x.prediction.model_output for x in selections])
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
        self.setMinimumWidth(200)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        combo_box = QtWidgets.QComboBox()
        combo_box.addItem("Speed Analysis")
        combo_box.addItem("Model Analysis")
        combo_box.addItem("Stats Analysis")
        layout.addWidget(combo_box)
        combo_box.currentIndexChanged.connect(
            lambda index: self.change_analysis(index, event))
        layout.addSpacerItem(QtWidgets.QSpacerItem(0, 5))
        layout.addWidget(EventSpeedWidget(event))

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
            layout.addWidget(EventSpeedWidget(event))
        elif index == 1:
            layout.addWidget(EventModelWidget(event))
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
        self.setMaximumWidth(200)

        layout.addWidget(SubtitleLabel(f"Meeting Name"))
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

        layout.addWidget(SubtitleLabel(f"Track Condition"))
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
        layout.setContentsMargins(0, 0, 0, 0)
        meeting_info_widget = MeetingInfoWidget(meeting)
        events_widget = EventsWidget(meeting)
        layout.addWidget(meeting_info_widget)
        layout.addWidget(events_widget)


class ScraperTab(QtWidgets.QWidget):
    def __init__(self, scraper: MeetingsScraper):
        super(ScraperTab, self).__init__()

        self.scraper = scraper
        self.meetings: list[Meeting] = []
        horizontal_layout = QtWidgets.QHBoxLayout()
        self.setLayout(horizontal_layout)

        date_widget = QtWidgets.QWidget()
        date_widget.setMaximumWidth(200)
        date_widget.setMinimumWidth(200)
        date_form = QtWidgets.QFormLayout()
        date_widget.setLayout(date_form)
        label = QtWidgets.QLabel("Date to Scrape")
        label.setStyleSheet(
            "font-size: 20px; font-weight: bold; text-decoration: underline;")
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

        meetings_widget = QtWidgets.QWidget()
        meetings_widget.setMaximumWidth(1000)
        meetings_widget.setMinimumWidth(1000)
        meetings_form = QtWidgets.QFormLayout()
        meetings_widget.setLayout(meetings_form)
        # 50% of the screen width
        self.meetings_layout = QtWidgets.QVBoxLayout()
        meetings_form.addRow(self.meetings_layout)
        horizontal_layout.addWidget(date_widget)
        horizontal_layout.addWidget(meetings_widget)
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
        for i in reversed(range(self.meetings_layout.count())):
            self.meetings_layout.itemAt(i).widget().setParent(None)
        self.scrape_button.setEnabled(False)
        self.scrape_button.setText("Extracting...")
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.update()

        scrape_date = datetime(date.year(), date.month(), date.day())
        self.meetings = self.scraper.get_meetings(scrape_date)
        with open("meetings.txt", "w") as file:
            for meeting in self.meetings:
                file.write(str(meeting) + "\n")
        # with open("meetings.txt", "r") as file:
        #     self.meetings = []
        #     for line in file.readlines():
        #         self.meetings.append(eval(line))
        state_dict = group_by_state(self.meetings)
        for state, meetings in state_dict.items():
            state_frame = self.create_state_frame(state, meetings)
            self.meetings_layout.addWidget(state_frame)

        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.scrape_button.setText("Extract")
        self.scrape_button.setEnabled(True)

    def create_state_frame(
            self, state: str, meetings: list[Meeting]) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout()
        title_label = QtWidgets.QLabel(state)
        title_label.setStyleSheet("font-size: 30px; font-weight: bold;")
        layout.addWidget(title_label)
        horizontal_line = QHLine()
        layout.addWidget(horizontal_line)
        horizontal_layout = QtWidgets.QHBoxLayout()
        for meeting in meetings:
            meeting_name = meeting.name
            button = QtWidgets.QPushButton(meeting_name)
            button.setMaximumWidth(200)
            button.setMinimumWidth(200)
            button.setCursor(QtGui.QCursor(
                QtCore.Qt.CursorShape.PointingHandCursor))
            button.clicked.connect(self.open_meeting_window)
            button.setFixedHeight(30)
            horizontal_layout.addWidget(button)

        horizontal_layout.addStretch()
        for widget in horizontal_layout.children():
            if type(widget) is QtWidgets.QPushButton:
                print(widget.text())
        layout.addLayout(horizontal_layout)
        frame.setLayout(layout)
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
        window_layout.setContentsMargins(10, 10, 10, 10)
        # set to screen size
        app = MeetingScraperApp.instance()
        if type(app) is MeetingScraperApp:
            screen_size = app.primaryScreen().size()
            widget.setMaximumSize(screen_size)
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
        window = MainWindow(scraper)
        window.showMaximized()

        return self.exec()
