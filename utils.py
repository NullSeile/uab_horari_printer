import datetime
from enum import IntEnum
from typing import Dict, List, Optional


class SubjectProps:
    def __init__(self, name: str, color: str):
        self.name = name
        self.color = color


class SubjectType(IntEnum):
    UNKNOWN = -1
    THEORY = 0
    SEMINAR = 1
    PROBLEMS = 2
    LABORATORY = 3
    EXAM = 4

    def __str__(self):
        return self.name


class HolidayType(IntEnum):
    FESTIU = 0
    NO_LECTIU = 1


# Stores information of a subject
class Subject:
    def __init__(self):
        self.id: str = None
        self.group: str = None
        self.type: SubjectType = None
        self.classroom: str = None

    def __str__(self):
        return f"{self.id}: {self.group} - {self.type} at {self.classroom}"

    def __repr__(self):
        return f"Subject({self})"


class Day:
    def __init__(self):
        self.hours: Dict[int, List[Subject]] = dict()  # key = hour, value = subject
        self.holiday: Optional[HolidayType] = None
        self.date: datetime.date = None

    def add_subject(self, hour, subject):
        if hour not in self.hours.keys():
            self.hours[hour] = list()

        self.hours[hour].append(subject)

    def __str__(self):
        return f"holiday={self.holiday} {self.hours}"


class Week:
    def __init__(self, date: datetime.date):
        self.days = {
            0: Day(),  # Monday
            1: Day(),  # Tuesday
            2: Day(),  # Wednesday
            3: Day(),  # Thursday
            4: Day(),  # Friday
        }
        for day_n, day in self.days.items():
            day.date = date + datetime.timedelta(days=day_n)

    def __getitem__(self, day):
        assert 0 <= day < 5, "Day must be a number between 0 and 4"
        return self.days[day]
