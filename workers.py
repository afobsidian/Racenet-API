from __future__ import annotations

from datetime import datetime

from PySide6 import QtCore

from cache_utils import load_meetings_cache, save_meetings_cache
from meetings_data import Meeting
from scraper import MeetingsScraper


class MeetingsLoadWorker(QtCore.QObject):
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(
        self,
        scraper: MeetingsScraper,
        scrape_date: datetime,
        use_local_data: bool,
        cache_path: str = "meetings_cache.json",
    ):
        super().__init__()
        self.scraper = scraper
        self.scrape_date = scrape_date
        self.use_local_data = use_local_data
        self.cache_path = cache_path

    @QtCore.Slot()
    def run(self):
        try:
            meetings = self._load_meetings()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(meetings)

    def _load_meetings(self) -> list[Meeting]:
        if self.use_local_data:
            meetings = load_meetings_cache(self.cache_path)
            self.scraper.apply_predictor_settings_to_meetings(meetings)
            return meetings

        meetings = self.scraper.get_meetings(self.scrape_date)
        save_meetings_cache(self.cache_path, meetings)
        return meetings
