import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options
from app.modules.auth.services import AuthenticationService
from app import create_app,db

FIREFOX_BIN = "/snap/firefox/current/usr/lib/firefox/firefox"

class TestExistentsendemail():
  def setup_method(self, method):
    options = Options()
    options.binary_location = FIREFOX_BIN
    options.add_argument("--headless=new")
    self.driver = webdriver.Firefox(options=options)
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_existentsendemail(self):
    self.driver.get("http://127.0.0.1:5000/")
    self.driver.set_window_size(1340, 833)
    self.driver.find_element(By.CSS_SELECTOR, ".sidebar-link > .feather-log-in").click()
    self.driver.find_element(By.LINK_TEXT, "Forgot your password?").click()
    self.driver.find_element(By.ID, "email").click()
    self.driver.find_element(By.ID, "email").send_keys("user1@example.com")
    self.driver.find_element(By.CSS_SELECTOR, ".content").click()
    self.driver.find_element(By.ID, "submit").click()

class TestNonexistent():
  def setup_method(self, method):
    options = Options()
    options.binary_location = FIREFOX_BIN
    options.add_argument("--headless=new")
    self.driver = webdriver.Firefox(options=options)
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_nonexistent(self):
    try:
      self.driver.get("http://127.0.0.1:5000/")
      self.driver.set_window_size(1978, 1125)
      self.driver.find_element(By.CSS_SELECTOR, ".sidebar-nav").click()
      self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(6) .align-middle:nth-child(2)").click()
      self.driver.find_element(By.LINK_TEXT, "Forgot your password?").click()
      self.driver.find_element(By.ID, "email").click()
      self.driver.find_element(By.ID, "email").send_keys("noexist@gmail.com")
      self.driver.find_element(By.ID, "submit").click()
    except Exception:
      pytest.fail("The email address is not registered in our system.")

class TestResetpassword():
  def setup_method(self, method):
    options = Options()
    options.binary_location = FIREFOX_BIN
    options.add_argument("--headless=new")
    self.driver = webdriver.Firefox(options=options)
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_resetpassword(self):

    app = create_app("development")

    with app.app_context():
      service = AuthenticationService()
      user = service.repository.get_by_email("user1@example.com")

      if not user:
        user = service.create_with_profile(
          name="John",
          surname="Doe",
          email="user1@example.com",
          password="1234"
        )

      token = user.generate_reset_token()
    
    self.driver.get(f"http://127.0.0.1:5000/reset-password/{token}")
    self.driver.set_window_size(1978, 1125)
    
    self.driver.find_element(By.ID, "password").click()
    self.driver.find_element(By.ID, "password").send_keys("1234")
    self.driver.find_element(By.ID, "confirm_password").click()
    self.driver.find_element(By.ID, "confirm_password").send_keys("1234")
    self.driver.find_element(By.ID, "submit").click()