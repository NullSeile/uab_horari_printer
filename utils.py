from ctypes import Union
import datetime
from enum import IntEnum
from typing import Dict, List


class SubjectProps:
	def __init__(self, name: str, color: str):
		self.name = name
		self.color = color

# Which subjects to get (short name and color)
SUBJECT_PROPS = {
    "100095": SubjectProps("GL", "#ffd28a"),
    "100098": SubjectProps("SMD", "#afeeee"),
    "100096": SubjectProps("EA", "#e9ffa4"),
    "100099": SubjectProps("TM", "#ffb3ad"),
    "100087": SubjectProps("FVR", "#aba6ff"),
}

# Month number to month name
MONTH_NAME = [
    "gen",
    "febr",
    "març",
    "abr",
    "maig",
    "juny",
    "jul",
    "ago",
    "set",
    "oct",
    "nov",
    "des",
]


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
        self.holiday: Union[None, HolidayType] = None
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
