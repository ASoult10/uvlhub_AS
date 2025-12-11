import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver, close_driver

def test_edit_profile_page():
    """Test que permite editar el perfil de un usuario"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")

        # Login
        try:
            driver.find_element(By.LINK_TEXT, "Login").click()
            driver.find_element(By.ID, "email").send_keys("user1@example.com")
            driver.find_element(By.ID, "password").send_keys("1234")
            driver.find_element(By.ID, "remember_me").click()
            driver.find_element(By.ID, "submit").click()
        except NoSuchElementException:
            raise AssertionError("Login page did not load correctly!")

        # Open Edit Profile
        try:
            driver.find_element(By.CSS_SELECTOR, ".hamburger").click()
            driver.find_element(By.LINK_TEXT, "Edit profile").click()
        except NoSuchElementException:
            raise AssertionError("Edit profile link/button not found!")

        # Fill profile fields
        try:
            affiliation_field = driver.find_element(By.ID, "affiliation")
            affiliation_field.clear()
            affiliation_field.send_keys("Seville Uni")

            orcid_field = driver.find_element(By.ID, "orcid")
            orcid_field.clear()
            orcid_field.send_keys("1111-2222-3333-4444")

            driver.find_element(By.ID, "submit").click()
            print("Profile edit test passed!")
        except NoSuchElementException:
            raise AssertionError("Profile fields not found!")

    finally:
        close_driver(driver)

if __name__ == "__main__":
    test_edit_profile_page()