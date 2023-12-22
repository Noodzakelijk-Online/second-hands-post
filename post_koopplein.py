from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from decouple import config
from nlp_hanlder import get_best_match
import time
import re
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView();", element)
    time.sleep(0.5)  # Allow some time for scrolling

def accept_cookies_if_present(driver, timeout=10):
    """Click the accept cookies button if it's present."""
    try:
        # Wait for the cookie acceptance button to be present
        accept_button = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, 'qball_co_cookie-close-button'))
        )
        accept_button.click()
        print("Accepted cookies.")
    except TimeoutException:
        # This will be raised if the button is not present after `timeout` seconds
        print("Cookie acceptance modal did not appear.")

def login_koopplein(driver, vault):
    """Login to koopplein.nl using credentials from LastPass."""
    website_url = config("KOOPPLEIN_URL")
    account = next((item for item in vault.accounts if item.url.decode('utf-8') == website_url), None)
    if not account:
        print("KOOPPLEIN account not found in LastPass vault!")
        exit()

    # Open a new tab
    driver.execute_script("window.open('about:blank', 'tab4');")
    driver.switch_to.window("tab4")

    # Navigate to koopplein.com
    driver.get(website_url)

    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)

    time.sleep(0.5)
    # Find the login button and click it.
    time.sleep(2)
    # Wait for login page load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, 'login_submit')))
    # Find the input fields for email and password. Adjust these selectors if they don't match the website's current design
    email_input = driver.find_element(By.ID, 'login_email')
    password_input = driver.find_element(By.ID, 'login_password')
    email_input.send_keys(account.username.decode('utf-8'))
    password_input.send_keys(account.password.decode('utf-8'))

    # Click login
    driver.find_element(By.ID, 'login_submit').click()

    time.sleep(10)

def post_listing_on_koopplein(driver, listing):
    """Post a scraped listing to nextdoor.com."""
    # Create a webdriverwait object
    wait = WebDriverWait(driver, 10)

    time.sleep(2)
    
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.place-ad-button.place-ad-button-desktop')))
    post_button = driver.find_element(By.CSS_SELECTOR, '.place-ad-button.place-ad-button-desktop')
    # Using JavaScript to scroll to the button
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.2)
    post_button.click()
    time.sleep(2)
    # Select advertise as "Private or Company or Club"
    find_category_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Particulier')))
    # scroll_to_element(driver, find_category_button)  # Scroll to find category button
    find_category_button.click()
    next_button = driver.find_element(By.CSS_SELECTOR, 'form[action="https://koopplein.nl/arnhem/advertenties/edit"] button.submit-button.button')
    driver.execute_script("arguments[0].scrollIntoView();", next_button)
    driver.execute_script("window.scrollBy(0, -120);")
    next_button.click()

    # Type main content of the ad
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#advert_submit')))
    time.sleep(1)


    # Main Category
    main_category_element = driver.find_element(By.ID, 'advert_parent_category')
    select_main_category = Select(main_category_element)
    main_category_options = driver.find_elements(By.CSS_SELECTOR, '#advert_parent_category option:not(:first-child)')
    main_category_lists = [element.text for element in main_category_options]
    best_match_index = get_best_match(listing["Category"], main_category_lists)
    if best_match_index < len(main_category_lists):
        select_main_category.select_by_index(best_match_index + 1) # This is because we skipped the first option
    else:
        print(f"Index {best_match_index} is out of range for the available categories.")
        select_main_category.select_by_index(1)

    # Sub category
    time.sleep(3)
    sub_category_element = driver.find_element(By.ID, 'advert_category')
    select_sub_category = Select(sub_category_element)
    sub_category_options = driver.find_elements(By.CSS_SELECTOR, '#advert_category option:not(:first-child)')
    sub_category_lists = [element.text for element in sub_category_options]
    if (len(sub_category_lists) != 0):
        best_match_index = get_best_match(listing["Category"], sub_category_lists)
        if best_match_index < len(sub_category_lists):
            select_sub_category.select_by_index(best_match_index + 1) # This is because we skipped the first option
        else:
            print(f"Index {best_match_index} is out of range for the available categories.")
            select_sub_category.select_by_index(1)


    # Select condition
    condition_element = driver.find_element(By.ID, 'new_product')
    select_condition = Select(condition_element)
    select_condition.select_by_value("0")

    # Title
    driver.find_element(By.ID, 'advert_title').send_keys(listing["Title"])

    # Price
    price_element = driver.find_element(By.ID, 'advert_price_type')
    select_price = Select(price_element)
    select_price.select_by_value("8")

    # Check for not accepting bids
    driver.find_element(By.ID, 'advert_no_bids').click()

    driver.find_element(By.ID, 'advert_description').send_keys(listing["Description"])

    upload_element = driver.find_element(By.CSS_SELECTOR, '#advert_container_files input[type="file"]')

    image_paths = listing["Image Paths"]
    absolute_image_paths = "\n".join(os.path.join(os.getcwd(), path) for path in image_paths)
    input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#advert_container_files input[type="file"]')))
    driver.execute_script('arguments[0].style.visibility= "visible";', input_element)
    time.sleep(1)
    input_element.send_keys(absolute_image_paths)
    time.sleep(5)

    driver.find_element(By.ID, 'advert_submit').click()
    time.sleep(0.5)

    # Click post now button
    post_now_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'form[action="https://koopplein.nl/arnhem/advertenties/edit"] input.account-content-button[type="submit"]')))
    time.sleep(0.3)
    post_now_button.click()
    time.sleep(3)


def get_koopplein_titles(driver):

    # # Navigate to the my postings page
    # driver.get('https://koopplein.nl/arnhem/gebruikers/2932588/robert-velhorst')
    # time.sleep(2)
    # Accept cookies if the modal appears
    # accept_cookies_if_present(driver)
    # scroll_to_end(driver)
    
    time.sleep(5)
    # Now get all the titles
    titles = [e.text for e in driver.find_elements(By.CSS_SELECTOR, 'tbody.account-content-list-content tr[itemprop="makesOffer"] td.list-title a')]
    return titles