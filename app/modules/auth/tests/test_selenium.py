import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver
from app import create_app
from app.modules.auth.services import AuthenticationService

def test_login_and_check_element():

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        # Wait a little while to ensure that the action has been completed
        time.sleep(4)

        try:

            driver.find_element(By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
            print("Test passed!")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:

        # Close the browser
        close_driver(driver)

# RECOVER MY PASSWORD TESTS

def test_recover_password_existing_email():

    driver = initialize_driver()

    try:

        driver.get(f"http://127.0.0.1:5000/")

        driver.find_element(By.CSS_SELECTOR, ".sidebar-link > .feather-log-in").click()
        driver.find_element(By.LINK_TEXT, "Forgot your password?").click()

        email_field = driver.find_element(By.ID, "email")
        email_field.send_keys("user1@example.com")

        driver.find_element(By.ID, "submit").click()

        print("Recover password with existing email PASSED")

    finally:
        close_driver(driver)

def test_recover_password_nonexistent_email():

    driver = initialize_driver()

    try:
        driver.get(f"http://127.0.0.1:5000/")

        driver.find_element(By.CSS_SELECTOR, ".sidebar-nav").click()
        driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(6) .align-middle:nth-child(2)").click()
        driver.find_element(By.LINK_TEXT, "Forgot your password?").click()

        email_field = driver.find_element(By.ID, "email")
        email_field.send_keys("noexist@gmail.com")

        driver.find_element(By.ID, "submit").click()

        print("Recover password with NON-existing email PASSED")

    finally:
        close_driver(driver)

def test_reset_password_valid_token():

    driver = initialize_driver()

    try:
        app = create_app("development")
        with app.app_context():
            service = AuthenticationService()

            user = service.repository.get_by_email("user1@example.com")
            if not user:
                user = service.create_with_profile(
                    name="Test", surname="User",
                    email="user1@example.com", password="1234"
                )

            token = user.generate_reset_token()

        driver.get(f"http://127.0.0.1:5000/reset-password/{token}")

        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "confirm_password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()

        print("Reset password using valid token → OK")

    finally:
        close_driver(driver)


if __name__ == "__main__":
    test_login_and_check_element()
    test_recover_password_existing_email()
    test_recover_password_nonexistent_email()
    test_reset_password_valid_token()
