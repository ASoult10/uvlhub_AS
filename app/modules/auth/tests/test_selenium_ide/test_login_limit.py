import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_login_rate_limit():
    """
    Tests that the login form shows a rate limit error after 3 failed attempts.
    """
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/login")
        time.sleep(2)  # Wait for page to load

        # Perform 3 failed login attempts
        for i in range(3):
            email_field = driver.find_element(By.NAME, "email")
            password_field = driver.find_element(By.NAME, "password")

            # Clear fields in case there's leftover text
            email_field.clear()
            password_field.clear()

            email_field.send_keys("baduser@example.com")
            password_field.send_keys("wrongpassword")
            password_field.send_keys(Keys.RETURN)

            time.sleep(2)  # Wait for page to process and reload

            # On the first 3 attempts, we expect an "Invalid credentials" error
            error_message = driver.find_element(By.XPATH, "//*[contains(text(), 'Invalid credentials')]")
            assert error_message.is_displayed()
            print(f"Attempt {i+1} failed as expected.")

        # Perform the 4th attempt, which should be blocked
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")
        email_field.clear()
        password_field.clear()
        email_field.send_keys("baduser@example.com")
        password_field.send_keys("wrongpassword")
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)

        # Now, we expect the rate limit error message
        try:
            rate_limit_error = driver.find_element(
                By.XPATH, "//*[contains(text(), 'You have exceeded the login attempt limit')]"
            )
            assert rate_limit_error.is_displayed()
            print("Test passed: Rate limit message was displayed on the 4th attempt.")
        except NoSuchElementException:
            raise AssertionError("Test failed: Rate limit error message was not found on the 4th attempt.")

    finally:
        # Close the browser
        close_driver(driver)
