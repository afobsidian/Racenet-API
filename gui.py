from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from meetings_data import Meeting, group_by_state, Event, Selection, Run, PositionSummary, FormBenchmark, Trainer, \
    Jockey, Prediction
from scraper import MeetingsScraper
from datetime import datetime
import qdarkstyle
import sys
from typing import Union
import multiprocessing


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


class LargeInfoLabel(QtWidgets.QLabel):
    def __init__(self, data: Union[str, int, float, object]):
        if type(data) is float:
            text = f"{data:.2f}"
        elif type(data) is int:
            text = f"{data:,}"
        elif type(data) is str:
            text = data
        else:
            text = str(data)
        super(LargeInfoLabel, self).__init__(text)
        self.setStyleSheet("font-size: 18px;")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)


class SmallInfoLabel(QtWidgets.QLabel):
    def __init__(self, data: Union[str, int, float, object]):
        if type(data) is float:
            text = f"{data:.2f}"
        elif type(data) is int:
            text = f"{data:,}"
        elif type(data) is str:
            text = data
        else:
            text = str(data)
        super(SmallInfoLabel, self).__init__(text)
        self.setStyleSheet("font-size: 14px;")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)


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


class SelectionSummaryWidget(QtWidgets.QWidget):
    def __init__(self, selection: Selection):
        super(SelectionSummaryWidget, self).__init__()
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(SmallInfoLabel(selection.number))
        layout.addWidget(SmallInfoLabel(selection.name))
        layout.addWidget(SmallInfoLabel(selection.barrier))
        layout.addWidget(SmallInfoLabel(selection.trainer.name))
        layout.addWidget(SmallInfoLabel(selection.jockey.name))
        layout.addWidget(SmallInfoLabel(selection.weight))
        layout.addWidget(SmallInfoLabel(selection.punters_edge))
        layout.addWidget(SmallInfoLabel(selection.prediction))


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
        self.setMinimumHeight(530)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.setIndentation(0)

        self.sections: list[tuple[Selection, QtWidgets.QFrame]] = []
        self.define_sections(selections)
        self.add_sections()

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
        if type(events_parent) is EventsWidget:
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


class EventsWidget(QtWidgets.QWidget):
    def __init__(self, meeting: Meeting):
        super(EventsWidget, self).__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            EventNumbersWidget(meeting), 0,
            QtCore.Qt.AlignmentFlag.AlignTop)
        self.event_tab_widget = EventsTabWidget(meeting)
        layout.addWidget(
            self.event_tab_widget, 1,
            QtCore.Qt.AlignmentFlag.AlignTop)

    def set_tab_index(self, index: int):
        self.event_tab_widget.setCurrentIndex(index)


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
        meeting_info_widget = MeetingInfoWidget(meeting)
        events_widget = EventsWidget(meeting)
        layout.addWidget(meeting_info_widget)
        layout.addWidget(events_widget)


class ScraperTab(QtWidgets.QWidget):
    def __init__(self):
        super(ScraperTab, self).__init__()

        self.scraper = MeetingsScraper()
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
        # with open("meetings.txt", "w") as file:
        #     for meeting in self.meetings:
        #         file.write(str(meeting) + "\n")
        with open("meetings.txt", "r") as file:
            self.meetings = []
            for line in file.readlines():
                self.meetings.append(eval(line))
        state_dict = group_by_state(self.meetings)
        for state, meetings in state_dict.items():
            state_frame = self.create_state_frame(state, meetings)
            self.meetings_layout.addWidget(state_frame)

        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.scrape_button.setText("Extract")
        self.scrape_button.setEnabled(True)

    def create_state_frame(self, state: str, meetings: list[Meeting]) -> QtWidgets.QFrame:
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
            (meeting for meeting in self.meetings if meeting.name == meeting_name))
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
    def __init__(self):
        super(MainWindow, self).__init__()

        widget = QtWidgets.QTabWidget()
        self.setCentralWidget(widget)
        widget.addTab(ScraperTab(), "Home")
        widget.setTabsClosable(True)
        widget.tabCloseRequested.connect(lambda index: widget.removeTab(index))
        # remove border inside tabs
        widget.setStyleSheet("QTabWidget::pane {border: 0;}")
        # widget.tabBar().hide()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
    app.setApplicationName("Meeting Scraper")
    app.setApplicationDisplayName("Meeting Scraper")
    app_font = QtGui.QFont()
    app_font.setFamily("Helvetica")
    app_font.setPointSize(14)
    app.setFont(app_font)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())
