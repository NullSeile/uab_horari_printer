from functools import partial
from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException

# from selenium.webdriver.remote.webelement import WebElement


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

starting_month = 2
starting_year = 2022

# How many weeks
number_of_weeks = 18

# If you want to skip any starting week
weeks_to_skip = 1


def try_until_success(method):
    while True:
        try:
            method()
            break
        except:
            pass


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

    driver.find_element(By.ID, "buscarCalendario").click()

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

    driver.find_element(By.ID, "comboMesesAnyos").click()
    driver.find_element(
        By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]'
    ).click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-event-container"))
    )

    while True:
        pass


if __name__ == "__main__":
    get_web_xml()
