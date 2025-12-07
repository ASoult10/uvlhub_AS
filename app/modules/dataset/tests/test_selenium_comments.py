import json
import time

import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


def test_dataset_comments_flow():
    """
    Flujo de prueba:
      - Login como user1@example.com
      - Abrir "Dataset with author 1"
      - Crear y ocultar un comentario
      - Crear y borrar otro comentario
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        time.sleep(2)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(2)
        wait_for_page_to_load(driver)

        driver.get(f"{host}/")
        wait_for_page_to_load(driver)

        dataset_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Dataset with author 1"))
        )
        dataset_link.click()
        wait_for_page_to_load(driver)

        comment_text_1 = f"comentario de prueba {int(time.time())}"

        textarea = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "commentContent")))
        textarea.clear()
        textarea.send_keys(comment_text_1)

        send_btn = driver.find_element(By.ID, "commentSendBtn")
        send_btn.click()

        WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.ID, "commentsList"), comment_text_1))

        comment_items = driver.find_elements(By.CLASS_NAME, "comment-item")
        target_item_1 = None
        for item in comment_items:
            if comment_text_1 in item.text:
                target_item_1 = item
                break

        assert target_item_1 is not None, "No se encontró el comentario para ocultar"

        hide_btn = target_item_1.find_element(By.CSS_SELECTOR, ".comment-actions .btn-outline-secondary")
        hide_btn.click()

        WebDriverWait(driver, 10).until_not(EC.text_to_be_present_in_element((By.ID, "commentsList"), comment_text_1))

        comment_text_2 = f"comentario de prueba borrar {int(time.time())}"

        textarea = driver.find_element(By.ID, "commentContent")
        textarea.clear()
        textarea.send_keys(comment_text_2)

        send_btn = driver.find_element(By.ID, "commentSendBtn")
        send_btn.click()

        WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.ID, "commentsList"), comment_text_2))

        comment_items = driver.find_elements(By.CLASS_NAME, "comment-item")
        target_item_2 = None
        for item in comment_items:
            if comment_text_2 in item.text:
                target_item_2 = item
                break

        assert target_item_2 is not None, "No se encontró el comentario para borrar"

        delete_btn = target_item_2.find_element(By.CSS_SELECTOR, ".comment-actions .btn-outline-danger")
        delete_btn.click()

        alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
        assert alert.text == "Delete this comment?"
        alert.accept()

        WebDriverWait(driver, 10).until_not(EC.text_to_be_present_in_element((By.ID, "commentsList"), comment_text_2))

        print("Dataset comments Selenium test passed!")

    except NoSuchElementException:

        raise AssertionError("Test failed!")

    finally:
        close_driver(driver)


test_dataset_comments_flow()
