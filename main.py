import sys
from scraper import MeetingsScraper
from gui import MeetingScraperApp

if __name__ == '__main__':
    scraper = MeetingsScraper()
    app = MeetingScraperApp()
    sys.exit(app.run(scraper))
