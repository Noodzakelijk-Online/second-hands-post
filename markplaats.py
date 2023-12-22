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
        consent_iframe_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[title="SP Consent Message"]'))
        )
        driver.switch_to.frame(consent_iframe_element)
        time.sleep(1)
        body_inside_iframe=driver.find_element(By.TAG_NAME, 'body')
        body_inside_iframe.find_element(By.CSS_SELECTOR, 'button[title="Accepteren"]').click()
        driver.switch_to.default_content()
        # # Wait for the cookie acceptance button to be present
        # accept_button = WebDriverWait(driver, timeout).until(
        #     EC.presence_of_element_located((By.ID, 'gdpr-consent-banner-accept-button'))
        # )
        # accept_button.click()
        print("Accepted cookies.")
    except TimeoutException:
        # This will be raised if the button is not present after `timeout` seconds
        print("Cookie acceptance modal did not appear.")

def login_markplaats(driver, vault):

    """Login to markplaats.com using credentials from LastPass."""
    website_url = config("MARKPLAATS_URL")
    account = next((item for item in vault.accounts if item.url.decode('utf-8') == website_url), None)
    if not account:
        print("Markplaats account not found in LastPass vault!")
        exit()

    # Open a new tab
    driver.execute_script("window.open('about:blank', 'tab3');")
    driver.switch_to.window("tab3")

    # Navigate to Markplaats.com
    driver.get(website_url)
    time.sleep(2)

    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)

    time.sleep(0.5)
    # Find the login button and click it.
    login_button = driver.find_element(By.CSS_SELECTOR, 'header a[data-role="login"]')
    time.sleep(2)
    login_button.click()
    # Wait for login page load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, 'account-login-button')))
    # Find the input fields for email and password. Adjust these selectors if they don't match the website's current design
    email_input = driver.find_element(By.ID, 'email')
    password_input = driver.find_element(By.ID, 'password')
    email_input.send_keys(account.username.decode('utf-8'))
    password_input.send_keys(account.password.decode('utf-8'))

    # Click login
    driver.find_element(By.ID, 'account-login-button').click()

    print("Login button is clicked, please check if the sms modal appears")
    time.sleep(10)

def post_listing_on_marktplaats(driver, listing):
    """Post a scraped listing to nextdoor.com."""
    if listing["Title"] == "Robot mop":
        print("Bypassing Robot mop")
        return
    # Create a webdriverwait object
    wait = WebDriverWait(driver, 10)

    time.sleep(2)
    
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-role="placeAd"]')))
    post_button = driver.find_element(By.CSS_SELECTOR, 'a[data-role="placeAd"]')
    # Using JavaScript to scroll to the button
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.2)
    post_button.click()
    time.sleep(0.2)
    # Find categories
    find_category_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#find-category')))
    scroll_to_element(driver, find_category_button)  # Scroll to find category button
    time.sleep(0.5)
    driver.find_element(By.CSS_SELECTOR, '#category-keywords').send_keys(listing["Title"])
    time.sleep(0.1)
    find_category_button.click()

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h2#cat_sug_list_label')))
    time.sleep(1)
    suggested_category_elements=driver.find_elements(By.CSS_SELECTOR, '.category-list-container ul.category-suggestions li.suggestion.item label span:first-child')
    suggested_category_lists = [element.text for element in suggested_category_elements]

    best_match_index = get_best_match(listing["Category"], suggested_category_lists)

    if best_match_index<len(suggested_category_elements):
        suggested_category_elements[best_match_index].click()
    else:
        print(f"Index {best_match_index} is out of range for the available categories.")
        suggested_category_elements[0].click() # Click 'other'

    # Click Further button
    driver.find_element(By.ID, 'category-selection-submit').click()

    # Wait for submit page displayed
    wait.until(EC.presence_of_element_located((By.ID, 'syi-place-ad-button')))
    
    desc_iframe_element = driver.find_element(By.ID, 'description_nl-NL_ifr')
    driver.switch_to.frame(desc_iframe_element)
    body_inside_iframe=driver.find_element(By.TAG_NAME, 'body')
    body_inside_iframe.send_keys(listing["Description"])
    driver.switch_to.default_content()

    # # Choose Price as 'To be agreed'
    # driver.find_element(By.CSS_SELECTOR, '#syi-price-type select').click()
    # time.sleep(0.2)
    # driver.find_element(By.CSS_SELECTOR, '#syi-price-type select option:nth-child(3)').click()

    select_element = driver.find_element(By.CSS_SELECTOR, '#syi-price-type select')
    select = Select(select_element)
    select.select_by_index(2)

    # Upload images
    wait.until(EC.presence_of_element_located((By.ID, 'uploader-container-0')))
    image_paths = listing["Image Paths"]
    absolute_image_paths = "\n".join(os.path.join(os.getcwd(), path) for path in image_paths)
    input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#uploader-container-0 input[type="file"]')))
    driver.execute_script('arguments[0].style.visibility= "visible";', input_element)
    time.sleep(1)
    input_element.send_keys(absolute_image_paths)
    time.sleep(5)
    # Select Delivery method as both Retrieve or Send
    driver.find_element(By.ID, 'Ophalen_of_Verzenden').click()
    time.sleep(1)
    # Find advertise how to
    freeplan = driver.find_element(By.CSS_SELECTOR, '.feature-selection .feature-column.left-feature')
    if '0,00' in freeplan.find_element(By.CSS_SELECTOR, 'span.price').text:
        freeplan.click()
        time.sleep(1)
        driver.find_element(By.ID, 'syi-place-ad-button').click()
        time.sleep(3)
        return True
    else:
        print("Sorry, we are not planning to pay. We prefer to use the free plan.")
        return False  # Make sure this is inside a function or method


def get_markplaats_titles(driver):

    # Navigate to the my postings page
    driver.get('https://www.marktplaats.nl/my-account/sell/index.html')
    time.sleep(2)
    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)
    # scroll_to_end(driver)
    
    time.sleep(10)
    # Now get all the titles
    titles = [e.text for e in driver.find_elements(By.CSS_SELECTOR, '.cells .description-title')]
    
    return titles