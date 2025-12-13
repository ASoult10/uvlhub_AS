import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

def test_hubfile_index():

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/hubfile")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:

            pass

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:

        # Close the browser
        close_driver(driver)


def test_verListaDeSavedModels():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")
        driver.set_window_size(1280, 716)
        driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
    except NoSuchElementException:
        raise AssertionError("Test failed!")
    finally:
        close_driver(driver)



def test_saveAndUnsaveModel():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/")
        driver.set_window_size(1067, 591)

        driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()

        driver.find_element(By.LINK_TEXT, "Dataset with tag5 and author 7").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-7 > span").click()

        driver.find_element(By.LINK_TEXT, "Saved models").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-7 > span").click()

        driver.find_element(
            By.CSS_SELECTOR,
            ".sidebar-item:nth-child(2) .align-middle:nth-child(2)"
        ).click()

        driver.find_element(By.LINK_TEXT, "Dataset with tag5 and author 7").click()

        driver.find_element(
            By.CSS_SELECTOR,
            ".sidebar-item:nth-child(9) .align-middle:nth-child(2)"
        ).click()

    except NoSuchElementException:
        raise AssertionError("Test failed!")

    finally:
        close_driver(driver)


def test_descargarMultiplesModelos():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/")
        driver.set_window_size(1119, 681)

        driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()

        driver.find_element(By.LINK_TEXT, "Dataset with tag5 and author 7").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-7 > span").click()

        driver.find_element(
            By.CSS_SELECTOR,
            ".sidebar-item:nth-child(2) .align-middle:nth-child(2)"
        ).click()

        driver.find_element(By.LINK_TEXT, "Dataset with author 1").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-6 > span").click()

        driver.find_element(
            By.CSS_SELECTOR,
            ".sidebar-item:nth-child(9) .align-middle:nth-child(2)"
        ).click()

        driver.find_element(By.LINK_TEXT, "Export All as JSON").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-6 > span").click()
        driver.find_element(By.CSS_SELECTOR, "#save-btn-7 > span").click()

    except NoSuchElementException:
        raise AssertionError("Test failed!")

    finally:
        close_driver(driver)



# Call the test function
test_hubfile_index()
test_verListaDeSavedModels()
test_saveAndUnsaveModel()
test_descargarMultiplesModelos()
