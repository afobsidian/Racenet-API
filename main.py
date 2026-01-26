import sys

from gui import MeetingScraperApp
from scraper import MeetingsScraper

if __name__ == "__main__":
    scraper = MeetingsScraper()
    app = MeetingScraperApp()
    sys.exit(app.run(scraper))
