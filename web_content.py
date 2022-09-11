import datetime
import re
from time import sleep
from typing import Callable, List

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup
import bs4.element

from utils import HolidayType, Subject, SubjectType, Week


def _try_until_success(method: Callable):
    while True:
        try:
            method()
            break
        except:
            pass


def _get_day_number_from_event(event: bs4.element.Tag):

    # Position in the screen of each day
    WEEKDAYS_X = [62, 207, 351, 495, 639, 779]  # Saturday

    position_re = re.search("(?<=left: ).*?(?=px;)", event.get("style"))
    if not position_re:
        raise Exception(f"How tf this doesn't have position? {event}")

    position = float(position_re.group(0))

    for i in range(5):
        if WEEKDAYS_X[i] <= position < WEEKDAYS_X[i + 1]:
            return i

    raise ValueError(f"{event} does not fit in any day")


def _parse_events_to_week(events: List[str], date: datetime.date) -> Week:
    week = Week(date)

    for event_html in events:
        event = BeautifulSoup(event_html, "html.parser").select(
            'div[class*="fc-event fc-event-vert fc-event-start fc-event-end"]'
        )[0]

        content = event.find("div", {"class": "fc-event-title"})
        day_n = _get_day_number_from_event(event)

        # Check if it's holiday
        if "Dia festiu" in content.getText():
            week[day_n].holiday = HolidayType.FESTIU

        elif "Dia no lectiu" in content.getText():
            week[day_n].holiday = HolidayType.NO_LECTIU

        else:
            content = str(content.find("p"))

            subject_id_re = re.search("(?<=<p>).*?(?= -)", content)
            if not subject_id_re:
                raise Exception(f"Something doesn't have a subject id? {content}")

            subject = Subject()

            subject_id = subject_id_re.group(0)
            subject.id = subject_id

            # Get the group
            group_text_re = re.search("(?<=Grup ).*?(?=<br/>)", content)
            if not group_text_re:
                raise Exception(f"There is not group? {content}")

            group_text = group_text_re.group(0)
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
            classroom = re.search("((?<=Aules )|(?<=Aula )).*?(?= -)", content)
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

    for day in week.days.values():
        if day.holiday is not None and day.hours:
            day.holiday = None

    return week


def get_weeks_from_web(
    subjects_id: List[str],
    starting_month: int,
    starting_year: int,
    weeks_to_skip: int,
    number_of_weeks: int,
) -> List[Week]:

    driver = webdriver.Chrome()

    driver.get(
        "https://web01.uab.es:31501/pds/consultaPublica/look%5Bconpub%5DInicioPubHora?entradaPublica=true&idioma=ca&pais=ES"
    )

    driver.find_element(By.ID, "tabAsignatura").click()

    for id in subjects_id:
        div = driver.find_element(By.CLASS_NAME, "bootstrap-tagsinput")
        input_text = div.find_element(By.CSS_SELECTOR, "input")
        input_text.send_keys(id)
        input_text.send_keys(Keys.ENTER)

        sleep(1)

        _try_until_success(lambda: driver.find_element(By.ID, "aceptarFiltro").click())

        sleep(1)

    # Click calendar
    _try_until_success(lambda: driver.find_element(By.ID, "buscarCalendario").click())

    # Force starting at start of the requested month and year
    driver.find_element(By.ID, "comboMesesAnyos").click()
    driver.find_element(By.CSS_SELECTOR, f'option[value="9/{starting_year}"]').click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    driver.find_element(By.ID, "comboMesesAnyos").click()
    driver.find_element(By.CSS_SELECTOR, f'option[value="10/{starting_year}"]').click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    _try_until_success(lambda: driver.find_element(By.ID, "comboMesesAnyos").click())

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]')
        )
    )

    driver.find_element(
        By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]'
    ).click()
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

    # Fill the weeks list
    weeks: List[Week] = list()
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
            week = _parse_events_to_week(events, date)

        except TimeoutException:
            print(f"WARNING: No events in week {i}")

        weeks.append(week)

        _try_until_success(driver.find_element(By.CLASS_NAME, "fc-button-next").click)
        date += datetime.timedelta(weeks=1)

    return weeks


# if __name__ == "__main__":
#     get_weeks_from_web(list(SUBJECT_PROPS.keys()))
