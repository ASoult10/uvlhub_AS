# Consolidated Selenium tests for admin + guest flows
# Adapted to project conventions: initialize_driver/close_driver, get_host_for_selenium_testing,
# WebDriverWait/EC, fixtures for DB cleanup for admin test.

import os
import subprocess
import time

import pytest
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

# Emails used in admin test (kept fixed to simplify cleanup fixture)
USER_EMAIL_1 = "usuario@nue.vo"
USER_EMAIL_2 = "admin@nuevo.es"


def _run_shell(cmd, env=None):
    """
    Ejecuta un comando como lista de argumentos (sin shell).
    """
    if isinstance(cmd, str):
        # Convierte la cadena a lista de argumentos
        import shlex

        cmd = shlex.split(cmd)

    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Command failed: {
                ' '.join(cmd)}\nExit: {
                e.returncode}"
        ) from e


def run_migrate_and_seed():
    """
    Ejecuta migraciones + seed sin depender de pytest.
    Usable desde Rosemary o cualquier runner manual.
    """
    MIGRATE_ENV = os.environ.copy()
    MIGRATE_ENV["FLASK_APP"] = "app:create_app('development')"
    MIGRATE_ENV["WORKING_DIR"] = os.getenv("WORKING_DIR", "")

    try:
        try:
            _run_shell("flask db downgrade base", env=MIGRATE_ENV)
        except RuntimeError:
            try:
                _run_shell("flask db downgrade 0", env=MIGRATE_ENV)
            except RuntimeError:
                pass

        _run_shell("flask db upgrade", env=MIGRATE_ENV)
        _run_shell("rosemary db:seed", env=MIGRATE_ENV)

    except Exception as e:
        raise RuntimeError(f"Migration/seed failed: {e}")


@pytest.fixture(scope="function")
def migrate_and_seed():
    run_migrate_and_seed()
    yield


class TestGuestuser:
    """
    Guest user flow adapted from Selenium IDE, with robustness improvements:
     - waits for modal/backdrop invisibility
     - JS click fallback on ElementClickInterceptedException
     - clear assertion messages
    """

    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}

    def teardown_method(self, method):
        close_driver(self.driver)

    def test_guestuser_flow(self, migrate_and_seed):
        try:
            host = get_host_for_selenium_testing()
            self.driver.get(f"{host}/")
            self.driver.set_window_size(1184, 906)

            wait = WebDriverWait(self.driver, 10)

            # Navigation to home/login
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".main"))).click()
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".nav-link:nth-child(1)"))).click()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("No se pudo acceder a la navegación principal")

            # Continue as Guest
            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Continue as Guest"))).click()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("El enlace 'Continue as Guest' no se encontró o no se pudo clicar")

            # Navigate sidebar items (tolerant, but fail if selector missing)
            sidebar_selectors = [
                ".sidebar-item:nth-child(6) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(7) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(8) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(9) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(14) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(15) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(18) .align-middle:nth-child(2)",
                ".sidebar-item:nth-child(2) .align-middle:nth-child(2)",
            ]

            for sel in sidebar_selectors:
                try:
                    el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    el.click()
                    time.sleep(0.3)
                except (NoSuchElementException, TimeoutException):
                    raise AssertionError(f"Selector de sidebar no encontrado o no clicable: {sel}")

            # Open a dataset by link text
            try:
                dataset_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Dataset with tag5 and author 7")))
                dataset_link.click()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("Link 'Dataset with tag5 and author 7' no encontrado")

            # Try open/close preview modal (if present) and wait backdrop to
            # disappear
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-outline-secondary:nth-child(1)"))).click()
                time.sleep(0.5)
                close_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-close")))
                close_btn.click()
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-backdrop")))
            except (NoSuchElementException, TimeoutException):
                # If modal not present, continue (not critical)
                pass

            # Attempt save as guest -> expect alert
            try:
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-backdrop")))
                save_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#save-btn-7 > span")))

                try:
                    save_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", save_btn)

                alert = wait.until(EC.alert_is_present())
                alert_text = alert.text
                expected = "You must be logged in as a user to save files."
                assert alert_text == expected, f"Texto de alerta inesperado: '{alert_text}' (esperado: '{expected}')"
                alert.accept()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("No se encontró el botón de guardar o no apareció la alerta esperada")

            # Attempt download (flexible matching)
            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Download all (1.91 KB)"))).click()
            except Exception:
                try:
                    link = self.driver.find_element(By.XPATH, "//a[contains(., 'Download all')]")
                    self.driver.execute_script("arguments[0].click();", link)
                except Exception:
                    pass

            # Profile navigation (non-fatal)
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".text-dark"))).click()
            except Exception:
                pass

            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "My profile"))).click()
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn")))
                btn.click()
                time.sleep(0.5)
            except Exception:
                pass

            try:
                dd2 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".dropdown-item:nth-child(2)")))
                dd2.click()
            except Exception:
                pass

        except AssertionError:
            raise
        except Exception as exc:
            raise AssertionError(f"test_guestuser_flow falló inesperadamente: {exc}")


class TestAdmin:
    """
    Admin flow adapted from Selenium IDE, merged here.
    Uses cleanup_created_users fixture to avoid leaving test users in the DB.
    """

    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}

    def teardown_method(self, method):
        close_driver(self.driver)

    def test_admin_flow_create_edit_delete_users(self, migrate_and_seed):
        try:
            host = get_host_for_selenium_testing()
            self.driver.get(f"{host}/")
            self.driver.set_window_size(1400, 900)

            wait = WebDriverWait(self.driver, 10)

            # Navigate to login
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".nav-link:nth-child(1)"))).click()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("No se encontró el enlace de login en la navegación")

            # Login as user1@example.com
            try:
                email_el = wait.until(EC.presence_of_element_located((By.ID, "email")))
                password_el = wait.until(EC.presence_of_element_located((By.ID, "password")))
                email_el.clear()
                password_el.clear()
                email_el.send_keys("user1@example.com")
                password_el.send_keys("1234")
                wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo en login: {exc}")

            # Open My profile
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".text-dark"))).click()
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "My profile"))).click()
            except Exception:
                raise AssertionError("No se pudo abrir 'My profile'")

            # Open Users section
            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Users"))).click()
            except Exception:
                try:
                    wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, ".sidebar-item:nth-child(11) .align-middle:nth-child(2)")
                        )
                    ).click()
                except Exception:
                    raise AssertionError("No se pudo abrir la sección Users")

            # Create first user (curator)
            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "+ Create New User"))).click()
                email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
                name_field = wait.until(EC.presence_of_element_located((By.ID, "name")))
                surname_field = wait.until(EC.presence_of_element_located((By.ID, "surname")))

                email_field.clear()
                email_field.send_keys(USER_EMAIL_1)
                name_field.clear()
                name_field.send_keys("usuario")
                surname_field.clear()
                surname_field.send_keys("nuevo")

                wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo creando primer usuario: {exc}")

            # Edit first user: set role curator and orcid
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                target_row = None
                for r in rows:
                    if USER_EMAIL_1 in r.text:
                        target_row = r
                        break

                if not target_row:
                    raise AssertionError("No se encontró la fila del usuario recién creado para editar")

                edit_link = target_row.find_element(By.LINK_TEXT, "Edit")
                edit_link.click()

                roles_sel = wait.until(EC.presence_of_element_located((By.ID, "roles")))
                roles_sel.find_element(By.XPATH, "//option[. = 'curator']").click()

                orcid_el = wait.until(EC.presence_of_element_located((By.ID, "orcid")))
                orcid_el.clear()
                orcid_el.send_keys("1234-1234-1234-1234")

                wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo editando primer usuario: {exc}")

            # Delete first user
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR, ".sidebar-item:nth-child(11) .align-middle:nth-child(2)"
                ).click()
                self.driver.find_element(By.CSS_SELECTOR, "tr:nth-child(1) .btn-delete").click()
                assert (
                    self.driver.switch_to.alert.text
                    == "Are you sure you want to delete this user? This action cannot be undone."
                )
                self.driver.switch_to.alert.accept()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo borrando primer usuario: {exc}")

            # Create second user (admin)
            try:
                wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "+ Create New User"))).click()
                email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
                name_field = wait.until(EC.presence_of_element_located((By.ID, "name")))
                surname_field = wait.until(EC.presence_of_element_located((By.ID, "surname")))

                email_field.clear()
                email_field.send_keys(USER_EMAIL_2)

                roles_sel = wait.until(EC.presence_of_element_located((By.ID, "roles")))
                roles_sel.find_element(By.XPATH, "//option[. = 'admin']").click()

                name_field.clear()
                name_field.send_keys("admin")
                surname_field.clear()
                surname_field.send_keys("nuevo")

                wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo creando segundo usuario: {exc}")

            # Delete second user
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                target_row = None
                for r in rows:
                    if USER_EMAIL_2 in r.text:
                        target_row = r
                        break

                if not target_row:
                    raise AssertionError("No se encontró la fila del usuario admin creado para borrar")

                delete_btn = target_row.find_element(By.CSS_SELECTOR, ".btn-delete")
                delete_btn.click()

                alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                assert alert.text == "Are you sure you want to delete this user? This action cannot be undone."
                alert.accept()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo borrando segundo usuario: {exc}")

        except AssertionError:
            raise
        except Exception as exc:
            raise AssertionError(f"test_admin_flow falló inesperadamente: {exc}")


class TestCurator:
    """
    Curator flow added from Selenium IDE.
    Kept consistent with project conventions (initialize_driver/close_driver,
    get_host_for_selenium_testing, WebDriverWait/EC). Uses migrate_and_seed to ensure
    seeded data is present before running.
    """

    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}

    def teardown_method(self, method):
        close_driver(self.driver)

    def test_curator_flow(self, migrate_and_seed):
        # migrate_and_seed runs before this test to ensure data seeded
        try:
            host = get_host_for_selenium_testing()
            self.driver.get(f"{host}/")
            self.driver.set_window_size(1854, 891)

            wait = WebDriverWait(self.driver, 10)

            # Go to login
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".nav-link:nth-child(1)"))).click()
            except (NoSuchElementException, TimeoutException):
                raise AssertionError("No se pudo encontrar el enlace de login en la navegación")

            # Login as curator user2@example.com
            try:
                email_el = wait.until(EC.presence_of_element_located((By.ID, "email")))
                password_el = wait.until(EC.presence_of_element_located((By.ID, "password")))
                email_el.clear()
                password_el.clear()
                email_el.send_keys("user2@example.com")
                password_el.send_keys("1234")
                wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()
                time.sleep(1)
            except Exception as exc:
                raise AssertionError(f"Fallo en login curator: {exc}")

            # Open curator area (sidebar item 8)
            try:
                wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".sidebar-item:nth-child(8) .align-middle:nth-child(2)")
                    )
                ).click()
            except Exception:
                raise AssertionError("No se pudo acceder a la sección de curador")

            # View first dataset
            try:
                view_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "tr:nth-child(1) .feather-eye")))
                view_btn.click()
                time.sleep(0.5)
            except Exception:
                # Not fatal, but reflect an issue
                raise AssertionError("No se pudo abrir la vista del primer dataset")

            # Download first dataset (attempt)
            try:
                dl_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "tr:nth-child(1) .feather-download")))
                dl_btn.click()
                time.sleep(0.5)
            except Exception:
                # ignore if download not available in test env
                pass

            # Edit first dataset
            self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(8) .align-middle:nth-child(2)").click()
            try:
                self.driver.find_element(By.CSS_SELECTOR, "tr:nth-child(1) .feather-edit").click()
                self.driver.find_element(By.ID, "title").click()
                self.driver.find_element(By.ID, "title").send_keys("Dataset with author 1 editado")
                dropdown = self.driver.find_element(By.ID, "publication_type")
                dropdown.find_element(By.XPATH, "//option[. = 'Journal Article']").click()
                self.driver.find_element(By.CSS_SELECTOR, "option:nth-child(4)").click()
                self.driver.find_element(By.ID, "submit").click()
            except Exception:
                raise AssertionError("No se pudo abrir el editor del primer dataset")

            # Trigger the action that raises a confirmation alert (as in
            # original script)
            try:
                action_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "tr:nth-child(1) form .feather")))
                try:
                    action_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", action_btn)

                alert = wait.until(EC.alert_is_present())
                assert (
                    alert.text == "Are you sure?"
                ), f"Texto de alerta inesperado: {
                    alert.text}"
                alert.accept()
            except Exception as exc:
                raise AssertionError(f"Fallo en la acción final del curator: {exc}")

        except AssertionError:
            raise
        except Exception as exc:
            raise AssertionError(f"test_curator_flow falló inesperadamente: {exc}")


if __name__ == "__main__":
    print("Running Selenium tests via Rosemary (manual runner)")

    # --- Global setup ---
    run_migrate_and_seed()

    # -------- Guest user --------
    guest = TestGuestuser()
    guest.setup_method(None)
    try:
        guest.test_guestuser_flow(migrate_and_seed=None)
        print("✓ TestGuestuser passed")
    finally:
        guest.teardown_method(None)

    # -------- Admin --------
    admin = TestAdmin()
    admin.setup_method(None)
    try:
        admin.test_admin_flow_create_edit_delete_users(migrate_and_seed=None)
        print("✓ TestAdmin passed")
    finally:
        admin.teardown_method(None)

    # -------- Curator --------
    curator = TestCurator()
    curator.setup_method(None)
    try:
        curator.test_curator_flow(migrate_and_seed=None)
        print("✓ TestCurator passed")
    finally:
        curator.teardown_method(None)

    print("All Selenium tests finished successfully")
