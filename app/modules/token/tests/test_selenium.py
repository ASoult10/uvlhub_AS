import time

from selenium.common.exceptions import NoSuchElementException

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


@pytest.fixture(scope="function")
def selenium_user(test_client):
    with test_client.application.app_context():
        auth_service = AuthenticationService()
        if auth_service.is_email_available(EMAIL):
            user = auth_service.create_with_profile(name=NAME, surname=SURNAME, email=EMAIL, password=PASSWORD)
    yield
    # Cleanup automático
    with test_client.application.app_context():
        user = auth_service.repository.get_by_email(EMAIL)
        if user:
            TokenService().revoke_all_tokens_for_user(user.id)


class TestSessions:
    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}
        self.token_service = TokenService()
        self.authentication_service = AuthenticationService()

        # Open the index page
        driver.get(f"{host}/token")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

    def test_getSessions(self, test_client, selenium_user):
        try:
            host = get_host_for_selenium_testing()
            self.driver.get(f"{host}/")
            self.driver.set_window_size(1051, 797)
            self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
            self.driver.find_element(By.ID, "email").click()
            self.driver.find_element(By.ID, "email").send_keys(EMAIL)
            self.driver.find_element(By.ID, "password").click()
            self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
            self.driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
            time.sleep(2)
            self.driver.find_element(By.LINK_TEXT, "Pan, Peter").click()
            self.driver.find_element(By.LINK_TEXT, "My profile").click()
            self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
            time.sleep(2)
            current_session_badge = self.driver.find_element(By.CSS_SELECTOR, "span.badge.bg-success.ms-1")
            assert current_session_badge.text == "Current Session"
        except Exception:
            pytest.fail("test_getSessions failed unexpectedly")

    def test_revokeToken(self, test_client, selenium_user):
        try:
            host = get_host_for_selenium_testing()
            self.driver.get(f"{host}/")
            self.driver.set_window_size(1552, 832)
            self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
            self.driver.find_element(By.ID, "email").click()
            self.driver.find_element(By.ID, "email").send_keys(EMAIL)
            self.driver.find_element(By.ID, "password").click()
            self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
            self.driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
            time.sleep(2)
            self.driver.find_element(By.CSS_SELECTOR, ".text-dark").click()
            self.driver.find_element(By.LINK_TEXT, "My profile").click()
            self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
            self.driver.find_element(By.CSS_SELECTOR, ".btn-sm").click()
            assert self.driver.switch_to.alert.text == "Are you sure you want to revoke this session?"
            self.driver.switch_to.alert.accept()
        except Exception:
            pytest.fail("test_revokeToken failed unexpectedly")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:

        # Close the browser
        close_driver(driver)


# Call the test function
test_token_index()
