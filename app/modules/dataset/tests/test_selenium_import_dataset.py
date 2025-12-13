import os
import tempfile
import time
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def login_user(driver, host):
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    email = driver.find_element(By.NAME, "email")
    password = driver.find_element(By.NAME, "password")

    email.send_keys("user1@example.com")
    password.send_keys("1234")
    password.send_keys(Keys.RETURN)

    time.sleep(2)
    wait_for_page_to_load(driver)


def create_temp_zip_with_files():
    tmp_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(tmp_fd)

    with zipfile.ZipFile(tmp_zip_path, "w") as zipf:
        zipf.writestr("example1.json", '{"demo": 1}')
        zipf.writestr("example2.uvl", "root FM {}")

    return tmp_zip_path


def test_import_dataset_zip():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        login_user(driver, host)

        driver.get(f"{host}/datasets/import")
        wait_for_page_to_load(driver)

        temp_zip_path = create_temp_zip_with_files()

        zip_input = driver.find_element(By.NAME, "zip_file")
        zip_input.send_keys(temp_zip_path)

        import_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Import')]")
        import_btn.click()

        time.sleep(3)
        wait_for_page_to_load(driver)

        result = driver.find_element(By.ID, "result").text.lower()

        assert "dataset imported successfully" in result, "ZIP import failed"

        print("✓ ZIP dataset import passed")

    finally:
        close_driver(driver)
        try:
            os.remove(temp_zip_path)
        except BaseException:
            pass


def test_import_dataset_github():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        login_user(driver, host)

        driver.get(f"{host}/datasets/import")
        wait_for_page_to_load(driver)

        github_input = driver.find_element(By.NAME, "github_url")
        github_input.send_keys("https://github.com/uiuc-cse/data-fa14")

        import_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Import')]")
        import_btn.click()

        time.sleep(4)
        wait_for_page_to_load(driver)

        result = driver.find_element(By.ID, "result").text.lower()

        assert "error" not in result, "GitHub import error"
        assert "dataset imported successfully" in result, "GitHub import failed"

        print("✓ GitHub dataset import passed")

    finally:
        close_driver(driver)
