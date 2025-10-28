import os

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


def initialize_driver():
    options = webdriver.FirefoxOptions()

    snap_tmp = os.path.expanduser("~/snap/firefox/common/tmp")
    os.makedirs(snap_tmp, exist_ok=True)
    os.environ["TMPDIR"] = snap_tmp

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    return driver


def close_driver(driver):
    driver.quit()
