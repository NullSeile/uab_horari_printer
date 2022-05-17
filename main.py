from render_timetable import render_to_pdf
from utils import SubjectProps
from web_content import get_weeks_from_web


subjects = {
    "100095": SubjectProps("GL", "#ffd28a"),
    "100098": SubjectProps("SMD", "#afeeee"),
    "100096": SubjectProps("EA", "#e9ffa4"),
    "100099": SubjectProps("TM", "#ffb3ad"),
    "100087": SubjectProps("FVR", "#aba6ff"),
}

weeks = get_weeks_from_web(
    list(subjects.keys()),
    starting_month=2,
    starting_year=2022,
    weeks_to_skip=1,
    number_of_weeks=21,
)

render_to_pdf(weeks, subjects)
