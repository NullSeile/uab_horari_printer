from asyncio import events
import datetime
from functools import partial
import re
from time import sleep
from typing import Callable, List
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup, Tag
import bs4.element

from utils import HolidayType, Subject, SubjectType, Week

# from selenium.webdriver.remote.webelement import WebElement


class SubjectProps:
    def __init__(self, name: str, color: str):
        self.name = name
        self.color = color


# Which subjects to get (short name and color)
SUBJECT_PROPS = {
    # "100095": SubjectProps("GL", "#ffd28a"),
    # "100098": SubjectProps("SMD", "#afeeee"),
    # "100096": SubjectProps("EA", "#e9ffa4"),
    # "100099": SubjectProps("TM", "#ffb3ad"),
    "100087": SubjectProps("FVR", "#aba6ff"),
}

starting_month = 2
starting_year = 2022

# How many weeks
number_of_weeks = 1

# If you want to skip any starting week
weeks_to_skip = 1


def try_until_success(method: Callable):
    while True:
        try:
            method()
            break
        except:
            pass


def get_day_number_from_event(event: bs4.element.Tag):

    print(event)
    print(event.get("style"))

    # Position in the screen of each day
    WEEKDAYS_X = [62, 207, 351, 495, 639, 779]  # Saturday

    position = float(re.search("(?<=left: ).*?(?=px;)", event.get("style")).group(0))

    for i in range(5):
        if WEEKDAYS_X[i] <= position < WEEKDAYS_X[i + 1]:
            return i

    raise ValueError(f"{event} does not fit in any day")


def parse_html_to_week(events: List[str], date: datetime.date) -> Week:
    # parsed = BeautifulSoup(html, "html.parser")

    week = Week(date)

    # for event in parsed.select(
    #     'div[class*="fc-event fc-event-vert fc-event-start fc-event-end"]'
    # ):
    for event_html in events:
        event = BeautifulSoup(event_html, "html.parser").select(
            'div[class*="fc-event fc-event-vert fc-event-start fc-event-end"]'
        )[0]

        content = event.find("div", {"class": "fc-event-title"})
        day_n = get_day_number_from_event(event)

        # Check if it's holiday
        if "Dia festiu" in content.getText():
            week[day_n].holiday = HolidayType.FESTIU

        elif "Dia no lectiu" in content.getText():
            week[day_n].holiday = HolidayType.NO_LECTIU

        else:
            content = str(content.find("p"))
            subject_id = re.search("(?<=<p>).*?(?= -)", content).group(0)

            if subject_id in SUBJECT_PROPS.keys():

                subject = Subject()

                subject.id = subject_id

                # Get the group
                group_text = re.search("(?<=Grup ).*?(?=<br/>)", content).group(0)
                subject.group = group_text[: group_text.find(" - ")]

                # Get the subject type
                type_text = group_text[group_text.find(" - ") + 3 :]
                if type_text == "Teoria":
                    subject.type = SubjectType.THEORY
                elif type_text == "Pràctiques d'Aula":
                    subject.type = SubjectType.PROBLEMS
                elif type_text == "Pràctiques de Laboratori":
                    subject.type = SubjectType.LABORATORY
                elif type_text == "Seminaris":
                    subject.type = SubjectType.SEMINAR
                elif type_text == "Examen":
                    subject.type = SubjectType.EXAM
                else:
                    subject.type = SubjectType.UNKNOWN
                    print(f"ERROR: {event} has not valid type '{type_text}'")

                # Get the classroom
                classroom = re.search("(?<=Aula ).*?(?= -)", content)
                if classroom is not None:
                    subject.classroom = classroom.group(0)
                else:
                    subject.classroom = ""

                # Get the hour
                hours = str(event.find("div", {"class": "fc-event-time"}).contents[0])

                start_time = int(hours[:2])
                end_time = int(hours[8:10])

                # Add the Subject
                for h in range(start_time, end_time):

                    week[day_n].add_subject(h, subject)

    return week


def get_web_xml():

    driver = webdriver.Chrome()

    driver.get(
        "https://web01.uab.es:31501/pds/consultaPublica/look%5Bconpub%5DInicioPubHora?entradaPublica=true&idioma=ca&pais=ES"
    )

    driver.find_element(By.ID, "tabAsignatura").click()

    for id in SUBJECT_PROPS.keys():
        div = driver.find_element(By.CLASS_NAME, "bootstrap-tagsinput")
        input_text = div.find_element(By.CSS_SELECTOR, "input")
        input_text.send_keys(id)
        input_text.send_keys(Keys.ENTER)

        sleep(1)

        try_until_success(lambda: driver.find_element(By.ID, "aceptarFiltro").click())

        sleep(1)

    try_until_success(lambda: driver.find_element(By.ID, "buscarCalendario").click())

    # Force starting at start of the requested month and year
    driver.find_element(By.ID, "comboMesesAnyos").click()
    driver.find_element(By.CSS_SELECTOR, f'option[value="9/2021"]').click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    driver.find_element(By.ID, "comboMesesAnyos").click()
    driver.find_element(By.CSS_SELECTOR, f'option[value="10/2021"]').click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    try_until_success(lambda: driver.find_element(By.ID, "comboMesesAnyos").click())

    driver.find_element(
        By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]'
    ).click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )
    # Skip the first `weeks_to_skip` weeks
    for _ in range(weeks_to_skip):
        driver.find_element(By.CLASS_NAME, "fc-button-next").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
        )

    # Get the starting day
    starting_day = int(driver.find_element(By.CLASS_NAME, "fc-header-title").text[:2])
    date = datetime.date(starting_year, starting_month, starting_day)
    for i in range(number_of_weeks):
        week = Week(date)

        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fc-event"))
            )

            events = [
                event.get_attribute("outerHTML")
                for event in driver.find_elements(By.CLASS_NAME, "fc-event")
            ]
            week = parse_html_to_week(events, date)

        except TimeoutException:
            print(f"WARNING: No events in week {i}")

        print(week)

        driver.find_element(By.CLASS_NAME, "fc-button-next").click()
        date += datetime.timedelta(weeks=1)

    # while True:
    #     pass


if __name__ == "__main__":
    get_web_xml()
