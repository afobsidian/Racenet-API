from __future__ import annotations

from typing import Optional

from PySide6 import QtCore

from meetings_data import Meeting


def meeting_key(meeting: Meeting) -> str:
    if meeting.meeting_id:
        return meeting.meeting_id
    if meeting.slug:
        return meeting.slug
    return f"{meeting.state}:{meeting.name}"


class AppState(QtCore.QObject):
    meetingsChanged = QtCore.Signal()
    selectedMeetingChanged = QtCore.Signal(object)
    analysisViewChanged = QtCore.Signal(str)
    loadingChanged = QtCore.Signal(bool)
    errorChanged = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self._meetings: list[Meeting] = []
        self._meetings_by_key: dict[str, Meeting] = {}
        self._selected_meeting_key = ""
        self._analysis_view_id = "model"
        self._loading = False
        self._error_message = ""

    @property
    def meetings(self) -> list[Meeting]:
        return self._meetings

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def analysis_view_id(self) -> str:
        return self._analysis_view_id

    def set_meetings(self, meetings: list[Meeting]):
        self._meetings = meetings
        self._meetings_by_key = {meeting_key(meeting): meeting for meeting in meetings}
        self.meetingsChanged.emit()

    def get_meeting(self, key: str) -> Optional[Meeting]:
        return self._meetings_by_key.get(key)

    def set_selected_meeting(self, key: str):
        if key == self._selected_meeting_key:
            meeting = self.get_meeting(key)
            if meeting is not None:
                self.selectedMeetingChanged.emit(meeting)
            return

        self._selected_meeting_key = key
        meeting = self.get_meeting(key)
        if meeting is not None:
            self.selectedMeetingChanged.emit(meeting)

    def set_analysis_view(self, view_id: str):
        if view_id == self._analysis_view_id:
            return
        self._analysis_view_id = view_id
        self.analysisViewChanged.emit(view_id)

    def set_loading(self, loading: bool):
        if loading == self._loading:
            return
        self._loading = loading
        self.loadingChanged.emit(loading)

    def set_error(self, message: str):
        if message == self._error_message:
            return
        self._error_message = message
        self.errorChanged.emit(message)
