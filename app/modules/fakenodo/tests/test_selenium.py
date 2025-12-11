import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


@pytest.fixture(scope="module")
def driver():
    driver = initialize_driver()
    yield driver
    close_driver(driver)


def wait_for_js_variable(driver, var_name, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                f"return typeof window.{var_name} !== 'undefined' && window.{var_name} !== null ? window.{var_name} : null"
            )
        )
    except TimeoutException:
        return None


#Pruebas de API

def test_01_render_main_page(driver):
    host = get_host_for_selenium_testing()
    driver.get(f"{host}/fakenodo/api/view")
    WebDriverWait(driver, 5).until(lambda d: "Fakenodo API Playground" in d.page_source)
    assert "Fakenodo API Playground" in driver.page_source


def test_02_create_deposition(driver):
    driver.execute_script(
        """
        fetch('/fakenodo/api/deposit/depositions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({metadata: {title: 'Selenium Test'}})
        })
        .then(r => r.ok ? r.json() : Promise.reject(r))
        .then(r => window.depositionId = r.id)
        .catch(() => window.depositionId = null);
    """
    )
    deposition_id = wait_for_js_variable(driver, "depositionId")
    assert deposition_id is not None
    driver.execute_script("window.lastDepositionId = window.depositionId;")


def test_03_list_depositions(driver):
    driver.execute_script(
        """
        fetch('/fakenodo/api/deposit/depositions')
            .then(r => r.ok ? r.json() : Promise.reject(r))
            .then(r => window.depositions = r.depositions)
            .catch(() => window.depositions = []);
    """
    )
    depositions = wait_for_js_variable(driver, "depositions")
    last_id = driver.execute_script("return window.lastDepositionId")
    assert depositions and any(d["id"] == last_id for d in depositions)


def test_04_get_deposition_detail(driver):
    last_id = driver.execute_script("return window.lastDepositionId")
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{last_id}')
            .then(r => r.ok ? r.json() : Promise.reject(r))
            .then(r => window.depositionDetail = r)
            .catch(() => window.depositionDetail = null);
    """
    )
    detail = wait_for_js_variable(driver, "depositionDetail")
    assert detail and detail["id"] == last_id
    assert "metadata" in detail and detail["metadata"]["title"] == "Selenium Test"


def test_05_upload_file(driver):
    last_id = driver.execute_script("return window.lastDepositionId")
    driver.execute_script(
        f"""
        var fd = new FormData();
        fd.append('filename', 'selenium.txt');
        fetch('/fakenodo/api/deposit/depositions/{last_id}/files', {{
            method: 'POST',
            body: fd
        }})
        .then(r => r.ok ? r.json() : Promise.reject(r))
        .then(r => window.uploadResult = r)
        .catch(() => window.uploadResult = null);
    """
    )
    upload_result = wait_for_js_variable(driver, "uploadResult")
    assert upload_result and upload_result["filename"] == "selenium.txt"
    assert "link" in upload_result


def test_06_publish_deposition(driver):
    last_id = driver.execute_script("return window.lastDepositionId")
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{last_id}/actions/publish', {{
            method: 'POST'
        }})
        .then(r => r.ok ? r.json() : Promise.reject(r))
        .then(r => window.publishResult = r)
        .catch(() => window.publishResult = null);
    """
    )
    publish_result = wait_for_js_variable(driver, "publishResult")
    assert publish_result and publish_result["id"] == last_id
    assert "doi" in publish_result


def test_07_delete_deposition(driver):
    last_id = driver.execute_script("return window.lastDepositionId")
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{last_id}', {{
            method: 'DELETE'
        }})
        .then(r => r.ok ? r.json() : Promise.reject(r))
        .then(r => window.deleteResult = r)
        .catch(() => window.deleteResult = null);
    """
    )
    delete_result = wait_for_js_variable(driver, "deleteResult")
    assert delete_result and "Deposition deleted" in delete_result["message"]


def test_08_get_nonexistent_deposition(driver):
    bad_id = 999999
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{bad_id}')
            .then(r => window.errorStatus = r.status)
            .catch(() => window.errorStatus = null);
    """
    )
    error_status = wait_for_js_variable(driver, "errorStatus")
    assert error_status == 404


def test_09_upload_file_nonexistent(driver):
    bad_id = 999999
    driver.execute_script(
        f"""
        var fd = new FormData();
        fd.append('filename', 'fail.txt');
        fetch('/fakenodo/api/deposit/depositions/{bad_id}/files', {{
            method: 'POST',
            body: fd
        }})
        .then(r => window.errorUploadStatus = r.status)
        .catch(() => window.errorUploadStatus = null);
    """
    )
    error_upload_status = wait_for_js_variable(driver, "errorUploadStatus")
    assert error_upload_status == 404


def test_10_publish_nonexistent_deposition(driver):
    bad_id = 999999
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{bad_id}/actions/publish', {{
            method: 'POST'
        }})
        .then(r => window.errorPublishStatus = r.status)
        .catch(() => window.errorPublishStatus = null);
    """
    )
    error_publish_status = wait_for_js_variable(driver, "errorPublishStatus")
    assert error_publish_status == 404


def test_11_delete_nonexistent_deposition(driver):
    bad_id = 999999
    driver.execute_script(
        f"""
        fetch('/fakenodo/api/deposit/depositions/{bad_id}', {{
            method: 'DELETE'
        }})
        .then(r => window.errorDeleteStatus = r.status)
        .catch(() => window.errorDeleteStatus = null);
    """
    )
    error_delete_status = wait_for_js_variable(driver, "errorDeleteStatus")
    assert error_delete_status == 404


#Pruebas de interfaz gráfica

def test_ui_create_deposition(driver):
    host = get_host_for_selenium_testing()
    driver.get(f"{host}/fakenodo/api/view")
    input_title = driver.find_element("id", "dep-title")
    input_title.clear()
    input_title.send_keys("Selenium UI Test")
    btn_create = driver.find_element("xpath", "//button[contains(., 'Crear depósito')]")
    btn_create.click()
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()
    WebDriverWait(driver, 5).until(lambda d: "Selenium UI Test" in d.page_source)
    assert "Selenium UI Test" in driver.page_source


def test_ui_list_depositions(driver):
    btn_update = driver.find_element("xpath", "//button[contains(., 'Actualizar lista')]")
    btn_update.click()
    ul = driver.find_element("id", "depositions-list")
    items = ul.find_elements("tag name", "li")
    assert any("Selenium UI Test" in item.text for item in items)


def test_ui_get_deposition_detail(driver):
    ul = driver.find_element("id", "depositions-list")
    items = ul.find_elements("tag name", "li")
    # Tomar el primer ID de la lista
    first_id = items[0].text.split(',')[0].split(':')[1].strip()
    input_id = driver.find_element("id", "dep-id")
    input_id.clear()
    input_id.send_keys(first_id)
    btn_detail = driver.find_element("xpath", "//button[contains(., 'Ver detalles')]")
    btn_detail.click()
    WebDriverWait(driver, 5).until(lambda d: "Selenium UI Test" in d.find_element("id", "deposition-detail").text)
    assert "Selenium UI Test" in driver.find_element("id", "deposition-detail").text


def test_ui_upload_file(driver):
    input_file = driver.find_element("id", "file-name")
    input_file.clear()
    input_file.send_keys("selenium_ui.txt")
    btn_upload = driver.find_element("xpath", "//button[contains(., 'Subir archivo')]")
    btn_upload.click()
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()


def test_ui_publish_deposition(driver):
    btn_publish = driver.find_element("xpath", "//button[contains(., 'Publicar')]")
    btn_publish.click()
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()


def test_ui_delete_deposition(driver):
    btn_delete = driver.find_element("xpath", "//button[contains(., 'Eliminar')]")
    btn_delete.click()
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()
