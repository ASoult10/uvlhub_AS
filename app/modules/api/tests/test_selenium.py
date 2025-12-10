import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_api_docs_page_loads():
    """Test que la página de documentación de API carga correctamente"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/api/docs")
        time.sleep(2)

        try:
            driver.find_element(By.TAG_NAME, "h1")
            page_source = driver.page_source.lower()
            assert "api" in page_source or "documentation" in page_source
            print("Test api_docs_page_loads passed!")
        except NoSuchElementException:
            raise AssertionError("API docs page did not load correctly!")

    finally:
        close_driver(driver)


def test_api_manage_requires_login():
    """Test que la página de gestión requiere login"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/api/manage")
        time.sleep(2)

        assert "/login" in driver.current_url
        print("Test api_manage_requires_login passed!")

    finally:
        close_driver(driver)


def test_create_api_key():
    """Test crear una API key después de hacer login"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            name_field = driver.find_element(By.NAME, "name")
            name_field.send_keys("Test API Key Selenium")

            scopes_checkboxes = driver.find_elements(By.NAME, "scopes")
            if scopes_checkboxes and not scopes_checkboxes[0].is_selected():
                scopes_checkboxes[0].click()
                time.sleep(0.5)

            submit_button = driver.find_element(By.NAME, "submit")
            submit_button.click()

            time.sleep(3)

            page_source = driver.page_source
            assert "Test API Key Selenium" in page_source or "success" in page_source.lower()

            print("Test create_api_key passed!")

        except NoSuchElementException:
            raise AssertionError("Could not create API key!")

    finally:
        close_driver(driver)


def test_create_api_key_multiple_scopes():
    """Test crear API key con múltiples scopes"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            driver.find_element(By.NAME, "name").send_keys("Multi Scope Key Selenium")

            scopes_to_select = ["read:datasets", "read:stats"]

            for scope_value in scopes_to_select:
                checkbox = driver.find_element(By.CSS_SELECTOR, f"input[name='scopes'][value='{scope_value}']")
                if not checkbox.is_selected():
                    checkbox.click()
                    time.sleep(0.5)

            time.sleep(1)

            driver.find_element(By.NAME, "submit").click()
            time.sleep(3)

            page_source = driver.page_source
            assert "Multi Scope Key Selenium" in page_source

            print("Test create_api_key_multiple_scopes passed!")

        except NoSuchElementException:
            raise AssertionError("Could not create API key with multiple scopes!")

    finally:
        close_driver(driver)


def test_api_key_table_display():
    """Test que las API keys se muestran en la tabla"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            page_source = driver.page_source.lower()
            assert "api" in page_source and ("key" in page_source or "clave" in page_source)

            print("Test api_key_table_display passed!")

        except NoSuchElementException:
            raise AssertionError("Could not find API key table!")

    finally:
        close_driver(driver)


def test_api_playground_page_loads():
    """Test que la página del playground carga correctamente (requiere login)"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            driver.find_element(By.ID, "ap_key")
            driver.find_element(By.ID, "ap_endpoint")
            driver.find_element(By.ID, "ap_send")
            print("Test api_playground_page_loads passed!")
        except NoSuchElementException:
            raise AssertionError("API playground did not load correctly!")

    finally:
        close_driver(driver)


def test_api_playground_test_datasets_endpoint():
    """Test probar endpoint /api/datasets desde el playground"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("test-key-123")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("datasets")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(3)

            response_body = driver.find_element(By.ID, "ap_body")
            assert response_body.text != "" and response_body.text != "Enviando..."

            print("Test api_playground_test_datasets_endpoint passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not test /api/datasets endpoint!")

    finally:
        close_driver(driver)


def test_api_playground_test_datasets_by_id():
    """Test probar endpoint /api/datasets/id/{id} desde el playground"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("test-key-123")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("datasets_id")
            time.sleep(1)

            ds_id_field = driver.find_element(By.ID, "ap_ds_id")
            ds_id_field.clear()
            ds_id_field.send_keys("1")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(3)

            response_body = driver.find_element(By.ID, "ap_body")
            assert response_body.text != ""

            print("Test api_playground_test_datasets_by_id passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not test /api/datasets/id endpoint!")

    finally:
        close_driver(driver)


def test_api_playground_test_datasets_by_title():
    """Test probar endpoint /api/datasets/title/{title} desde el playground"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("test-key-123")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("datasets_title")
            time.sleep(1)

            ds_title_field = driver.find_element(By.ID, "ap_ds_title")
            ds_title_field.clear()
            ds_title_field.send_keys("Test-Dataset")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(3)

            response_body = driver.find_element(By.ID, "ap_body")
            assert response_body.text != ""

            print("Test api_playground_test_datasets_by_title passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not test /api/datasets/title endpoint!")

    finally:
        close_driver(driver)


def test_api_playground_test_search_endpoint():
    """Test probar endpoint /api/search desde el playground"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("test-key-123")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("search")
            time.sleep(1)

            query_field = driver.find_element(By.ID, "ap_q")
            query_field.clear()
            query_field.send_keys("feature")
            time.sleep(1)

            page_field = driver.find_element(By.ID, "ap_page")
            page_field.clear()
            page_field.send_keys("1")
            time.sleep(1)

            per_page_field = driver.find_element(By.ID, "ap_per_page")
            per_page_field.clear()
            per_page_field.send_keys("10")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(3)

            response_body = driver.find_element(By.ID, "ap_body")
            assert response_body.text != ""

            print("Test api_playground_test_search_endpoint passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not test /api/search endpoint!")

    finally:
        close_driver(driver)


def test_api_playground_test_stats_endpoint():
    """Test probar endpoint /api/stats desde el playground"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("test-stats-key-123")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("stats")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(3)

            response_body = driver.find_element(By.ID, "ap_body")
            assert response_body.text != ""

            print("Test api_playground_test_stats_endpoint passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not test /api/stats endpoint!")

    finally:
        close_driver(driver)


def test_api_playground_check_curl_generation():
    """Test que el playground genera el comando cURL correctamente"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            api_key_field = driver.find_element(By.ID, "ap_key")
            api_key_field.clear()
            api_key_field.send_keys("my-test-key")
            time.sleep(1)

            endpoint_select = Select(driver.find_element(By.ID, "ap_endpoint"))
            endpoint_select.select_by_value("datasets")
            time.sleep(1)

            send_button = driver.find_element(By.ID, "ap_send")
            send_button.click()
            time.sleep(2)

            curl_code = driver.find_element(By.ID, "ap_curl")
            curl_text = curl_code.text
            assert "curl" in curl_text
            assert "my-test-key" in curl_text
            assert "/api/datasets" in curl_text

            print("Test api_playground_check_curl_generation passed!")
        except NoSuchElementException as e:
            print(f"Elemento no encontrado: {e}")
            raise AssertionError("Could not verify cURL generation!")

    finally:
        close_driver(driver)


def test_revoke_api_key():
    """Test revocar una API key existente"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            revoke_forms = driver.find_elements(By.XPATH, "//form[contains(@action, '/api/revoke/')]")

            if revoke_forms:
                revoke_button = revoke_forms[0].find_element(By.XPATH, ".//button[@type='submit']")
                revoke_button.click()
                time.sleep(1)
                driver.switch_to.alert.accept()
                time.sleep(2)

                page_source = driver.page_source.lower()
                assert "revoked" in page_source or "revocada" in page_source or "inactive" in page_source

                print("Test revoke_api_key passed!")
            else:
                print("No API keys to revoke, skipping test")

        except NoSuchElementException as e:
            print(f"Could not find revoke button: {e}")

    finally:
        close_driver(driver)


def test_delete_api_key():
    """Test eliminar una API key revocada"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)

        driver.get(f"{host}/api/manage")
        time.sleep(2)

        try:
            delete_forms = driver.find_elements(By.XPATH, "//form[contains(@action, '/api/delete/')]")

            if delete_forms:
                delete_button = delete_forms[0].find_element(By.XPATH, ".//button[@type='submit']")
                delete_button.click()
                time.sleep(1)
                driver.switch_to.alert.accept()
                time.sleep(2)

                page_source = driver.page_source.lower()
                assert "deleted" in page_source or "eliminada" in page_source or "success" in page_source

                print("Test delete_api_key passed!")
            else:
                print("No API keys to delete, skipping test")

        except NoSuchElementException as e:
            print(f"Could not find delete button: {e}")

    finally:
        close_driver(driver)


if __name__ == "__main__":
    test_api_docs_page_loads()
    test_api_manage_requires_login()
    test_create_api_key()
    test_create_api_key_multiple_scopes()
    test_api_key_table_display()
    test_api_playground_page_loads()
    test_api_playground_test_datasets_endpoint()
    test_api_playground_test_datasets_by_id()
    test_api_playground_test_datasets_by_title()
    test_api_playground_test_search_endpoint()
    test_api_playground_test_stats_endpoint()
    test_api_playground_check_curl_generation()
    test_revoke_api_key()
    test_delete_api_key()
