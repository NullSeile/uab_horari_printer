from ast import Sub
from render_timetable import render_to_pdf
from utils import SubjectProps
from web_content import get_weeks_from_web
import pickle

subjects = {
    # "104382": SubjectProps("C.Variable", "#ffd28a"),
    # "104381": SubjectProps("A.Lineal", "#afeeee"),
    "104383": SubjectProps("IalP", "#e9ffa4"),
    "104384": SubjectProps("FonCom", "#ffb3ad"),
    "104385": SubjectProps("ProSis", "#aba6ff"),
    # "104386": SubjectProps("Pro", "#e9ffa4"),
    # "104387": SubjectProps("CDV", "#ffb3ad"),
    # "104389": SubjectProps("POO", "#aba6ff"),
    # "104390": SubjectProps("CalNum", "#afeeee"),
}
# subjects = {
#     # "104382": SubjectProps("C.Variable", "#ffd28a"),
#     # "104381": SubjectProps("A.Lineal", "#afeeee"),
#     "104383": SubjectProps("I.Program", "#e9ffa4"),
#     "104384": SubjectProps("Fonaments", "#ffb3ad"),
#     "104385": SubjectProps("P.Sistema", "#aba6ff"),
# }

# subjects = {
#     "100095": SubjectProps("GL", "#ffd28a"),
#     "100098": SubjectProps("SMD", "#afeeee"),
#     # "100096": SubjectProps("EA", "#e9ffa4"),
#     # "100099": SubjectProps("TM", "#ffb3ad"),
#     "100087": SubjectProps("FVR", "#aba6ff"),
# }
# subjects = {
#     "102007": SubjectProps("CS i GE", "#ffffff", "61"),
#     "102024": SubjectProps("DP", "#ffffff", "61"),
#     "106734": SubjectProps("EDS", "#ffffff"),
#     "102024": SubjectProps("DP", "#ffffff"),
#     "100094": SubjectProps("AM", "#ffd28a"),  # Anàlisi
#     "100093": SubjectProps("CDV", "#afeeee"),  # Càlcul en diverses
#     "100106": SubjectProps("Top", "#aba6ff"),  # Topologia
#     "100095": SubjectProps("GL", "#aba6ff"),  # Geometria Lineal
#     "100087": SubjectProps("FVR", "#aba6ff"),  # Funcions
#     "100096": SubjectProps("EA", "#ffd28a"),
#     "100097": SubjectProps("MN", "#aba6ff"),
# }

weeks = get_weeks_from_web(
    subjects,
    starting_month=9,
    starting_year=2023,
    weeks_to_skip=0,
    number_of_weeks=22,
    # number_of_weeks=40,
)

with open("weeks.pik", "wb") as file:
    pickle.dump(weeks, file)

weeks = None
with open("weeks.pik", "rb") as file:
    weeks = pickle.load(file)

render_to_pdf(
    weeks,
    subjects,
    # start_hour=8,
    start_hour=9,
    end_hour=15,
)
