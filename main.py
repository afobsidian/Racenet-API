from scraper import MeetingsScraper

if __name__ == '__main__':
    scraper = MeetingsScraper()
    meetings = scraper.get_meetings()
    print(meetings[0])
