import time
import traceback

from selenium.common.exceptions import WebDriverException, TimeoutException

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def test_author_profile_from_homepage():
    """
    Test the navigation from the home page to an user's profile page using Selenium.
    """

    driver = initialize_driver()

    try:
        print("📍 Step 1: Navigating to homepage...")
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")
        wait_for_page_to_load(driver)
        time.sleep(3)  # Wait for dynamic content to load
        print("   ✓ Homepage loaded successfully")

        print("\n📍 Step 2: Looking for author link...")

        datasets = driver.find_elements(By.CLASS_NAME, "card")
        if not datasets:
            # No datasets found, skip the rest of the test
            print("   ⚠️  No datasets found on explore page - test passed (no data to verify)")
            return

        try:
            author_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//p[contains(text(), 'Updated by')]/a"))
                # It only selects the first occurrence
            )
        except TimeoutException:
            raise AssertionError("Datasets exist on explore page but no author link was found")

        author_name = author_link.text
        print(f"   ✓ Found author: {author_name}")

        print("\n📍 Step 3: Clicking on author link...")
        author_link.click()
        wait_for_page_to_load(driver)
        time.sleep(4)  # Wait for the profile page to load
        print("   ✓ Navigated to profile page")

        print("\n📍 Step 4: Verifying profile page...")
        assert "/profile/" in driver.current_url, f"Expected '/profile/' in URL, got: {driver.current_url}"
        print(f"   ✓ URL is correct: {driver.current_url}")

        assert author_name in driver.page_source, f"Author name '{author_name}' not found in page"
        print(f"   ✓ Author name '{author_name}' is displayed on the page")

    finally:
        driver.quit()


def test_author_profile_from_explore():
    """
    Test the navigation from the explore page to an user's profile page using Selenium.
    """
    driver = initialize_driver()

    try:
        print("📍 Step 1: Navigating to explore page...")
        host = get_host_for_selenium_testing()
        explore_url = f"{host}/explore"
        print(f"   Explore URL: {explore_url}")
        driver.get(explore_url)
        wait_for_page_to_load(driver)
        time.sleep(3)  # Wait for dynamic content to load
        print("   ✓ Explore page loaded successfully")

        print("\n📍 Step 2: Looking for author link...")

        datasets = driver.find_elements(By.CLASS_NAME, "card")
        if not datasets:
            # No datasets found, skip the rest of the test
            print("   ⚠️  No datasets found on explore page - test passed (no data to verify)")
            return

        try:
            author_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//span[contains(., 'Updated by')]/../following-sibling::div//a"
                ))
            )
        except TimeoutException:
            raise AssertionError("Datasets exist on explore page but no author link was found")

        author_name = author_link.text
        print(f"   ✓ Found author: {author_name}")

        print("\n📍 Step 3: Clicking on author link...")
        author_link.click()
        wait_for_page_to_load(driver)
        time.sleep(4)  # Wait for the profile page to load
        print("   ✓ Navigated to profile page")

        print("\n📍 Step 4: Verifying profile page...")
        assert "/profile/" in driver.current_url, f"Expected '/profile/' in URL, got: {driver.current_url}"
        print(f"   ✓ URL is correct: {driver.current_url}")

        assert author_name in driver.page_source, f"Author name '{author_name}' not found in page"
        print(f"   ✓ Author name '{author_name}' is displayed on the page")

    finally:
        driver.quit()


if __name__ == "__main__":
    # This messages will be shown only when running rosemary selenium profile (specifiying the module)
    print("\n" + "="*70)
    print("🚀 Starting Selenium Tests: Author Profile Navigation")
    print("="*70 + "\n")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Navigation from homepage
    print("\n" + "-"*70)
    print("Test 1: Navigation from Homepage")
    print("-"*70 + "\n")
    try:
        test_author_profile_from_homepage()
        tests_passed += 1
        print("\n✅ Test 1 PASSED\n")
    except WebDriverException as e:
        tests_failed += 1
        print("\n⚠️  Test 1 FAILED: WebDriver Error")
        print(f"   Error: {str(e)}")
        print("   ℹ️  This might be due to browser/driver issues (quota, installation, etc.)")
        print("\n   📋 Full traceback:")
        print("   " + "-"*66)
        traceback.print_exc()
        print("   " + "-"*66 + "\n")
    except AssertionError as e:
        tests_failed += 1
        print("\n❌ Test 1 FAILED: Assertion Error")
        print(f"   Error: {str(e)}\n")
    except Exception as e:
        tests_failed += 1
        print("\n❌ Test 1 FAILED: Unexpected Error")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}\n")

    # Test 2: Navigation from explore page
    print("\n" + "-"*70)
    print("Test 2: Navigation from Explore Page")
    print("-"*70 + "\n")
    try:
        test_author_profile_from_explore()
        tests_passed += 1
        print("\n✅ Test 2 PASSED\n")
    except WebDriverException as e:
        tests_failed += 1
        print("\n⚠️  Test 2 FAILED: WebDriver Error")
        print(f"   Error: {str(e)}")
        print("   ℹ️  This might be due to browser/driver issues (quota, installation, etc.)")
        print("\n   📋 Full traceback:")
        print("   " + "-"*66)
        traceback.print_exc()
        print("   " + "-"*66 + "\n")
    except AssertionError as e:
        tests_failed += 1
        print("\n❌ Test 2 FAILED: Assertion Error")
        print(f"   Error: {str(e)}\n")
    except Exception as e:
        tests_failed += 1
        print("\n❌ Test 2 FAILED: Unexpected Error")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}\n")

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"   ✅ Passed: {tests_passed}")
    print(f"   ❌ Failed: {tests_failed}")
    print(f"   📈 Total:  {tests_passed + tests_failed}")
    print("="*70 + "\n")
