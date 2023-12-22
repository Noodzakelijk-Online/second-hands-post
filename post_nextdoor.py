from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from decouple import config
from nlp_hanlder import get_best_match
import time
import re
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


def accept_cookies_if_present(driver, timeout=10):
    """Click the accept cookies button if it's present."""
    try:
        # Wait for the cookie acceptance button to be present
        accept_button = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, 'onetrust-accept-btn-handler'))
        )
        accept_button.click()
        print("Accepted cookies.")
    except TimeoutException:
        # This will be raised if the button is not present after `timeout` seconds
        print("Cookie acceptance modal did not appear.")

def login_nextdoor(driver, vault):
    """Login to nextdoor.com using credentials from LastPass."""
    website_url = config("NEXTDOOR_URL")
    account = next((item for item in vault.accounts if item.url.decode('utf-8') == website_url), None)
    if not account:
        print("Nextdoor account not found in LastPass vault!")
        exit()

    # Open a new tab
    driver.execute_script("window.open('about:blank', 'tab2');")
    driver.switch_to.window("tab2")

    # Navigate to nextdoor.com
    driver.get(website_url)

    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)

    # Find the input fields for email and password. Adjust these selectors if they don't match the website's current design
    email_input = driver.find_element(By.ID, 'id_email')
    password_input = driver.find_element(By.ID, 'id_password')
    email_input.send_keys(account.username.decode('utf-8'))
    password_input.send_keys(account.password.decode('utf-8'))

    # Click login
    driver.find_element(By.ID, 'signin_button').click()

    time.sleep(10)

def scroll_to_end(driver, timeout=0.5):
    """Scroll to the end of the page and wait for it to load."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Scroll to bottom of page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for the page to load
        time.sleep(timeout)
        
        # Calculate new scroll height and compare with the last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            break  # No more new items loaded
        
        last_height = new_height

def get_all_titles(driver):
    # Navigate to the my postings page
    driver.get('https://nextdoor.nl/for_sale_and_free/your_items/')
    time.sleep(2)
    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)
    scroll_to_end(driver)
    
    time.sleep(10)
    # Now get all the titles
    titles = [e.text for e in driver.find_elements(By.CSS_SELECTOR, '.classifieds-your-item-title-price-container h2')]
    
    return titles


def post_listing_on_nextdoor(driver, listing):
    """Post a scraped listing to nextdoor.com."""
    # Create a webdriverwait object
    wait = WebDriverWait(driver, 10)

    time.sleep(2)
    
    # Click the post button to open the modal
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button#main_content')))
    post_button = driver.find_element(By.ID, 'main_content')
    # Using JavaScript to scroll to the button
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    post_button.click()

    # Wait until an element within the modal appears, let's say it's the title input field
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="content-composer-dialog"] [data-testid="composer-finds-title"]')))
    # Fill in the form
    driver.find_element(By.CSS_SELECTOR, '[data-testid="composer-finds-title"]').send_keys(listing["Title"])
    driver.find_element(By.CSS_SELECTOR, '#finds-flow-textarea').send_keys(listing["Description"])
    numeric_price = extract_price(listing["Price"])
    driver.find_element(By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] > div:nth-child(10) input').send_keys(numeric_price)
    time.sleep(4)

    # Choose category
    driver.find_element(By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] > div:nth-child(7)' ).click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] div:not([class]) > div span')))
    best_match_index= get_best_match(listing["Category"], get_categories_on_nextdoor())

    elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] > div:not([class]) > div span')
    # Check if the index is valid for the list of elements
    if best_match_index<len(elements):
        elements[best_match_index].click()
    else:
        print(f"Index {best_match_index} is out of range for the available categories.")
        elements[0].click() # Click 'other'
    
    for image_path in listing["Image Paths"]:
        absolute_image_path = os.path.join(os.getcwd(), image_path)
        print(absolute_image_path)
        # Explicit wait until the input element is present and ready
        wait = WebDriverWait(driver, 10)
         # Find the modal
        modal_element = driver.find_element(By.CSS_SELECTOR, '[data-testid="content-composer-dialog"]')
        print("Modal found:", modal_element is not None)

    
        input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] .uploader-fileinput[accept="image/*"]')))
        # Scroll to the element
        driver.execute_script("arguments[0].scrollTop = arguments[1].offsetTop", modal_element, input_element)
        time.sleep(1)
        print("Executed JavaScript for scrolling.")
        driver.execute_script('arguments[0].style.visibility = "visible";', input_element)
        time.sleep(1)

        # Count the number of images already in the dropzone before uploading the next image
        current_image_count = len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="attachment-list-container-item"] img[data-testid="composer-image-attachment"]'))

        input_element.send_keys(absolute_image_path)
        # Wait for the number of images in the dropzone to increase by one
        wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="attachment-list-container-item"] img[data-testid="composer-image-attachment"]')) == current_image_count + 1)

        time.sleep(5)

    # Click the submit button
    driver.find_element(By.CSS_SELECTOR, '[data-testid="finds-subflow-composer"] [data-testid="composer-submit-button"]').click()
    time.sleep(1)
    # try:
    #     driver.find_element(By.CSS_SELECTOR, '[data-testid="attachment-manager-children-container"] [data-testid="composer-submit-button"]').click()
    #     time.sleep(1)
    # except Exception:
    #     print('Sequence submit button not appearing')
    # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="composer-submit-button"]')))
    # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="audience-menu-button"]')))
    time.sleep(3)
    driver.find_element(By.CSS_SELECTOR, '[data-testid="attachment-manager-children-container"] [data-testid="composer-submit-button"]').click()

    time.sleep(0.5)
    # Click the toast close button
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="fsf-after-posting-share-close"]')))
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR, 'button[data-testid="fsf-after-posting-share-close"]').click()


def get_categories_on_nextdoor():
    categories = [
        "Anders",
        "Apparaten",
        "Auto's en motoren",
        "Door buren aangeboden diensten",
        "Door een buurman/-vrouw gemaakt",
        "Electronica",
        "Fietsen en brommers",
        "Gereedschappen",
        "Huis en inrichting",
        "Huisdierbenodigdheden",
        "Kinderen en baby's",
        "Kleding en accessoires",
        "Meubels",
        "Muziek Instrumenten",
        "Op zoek naar",
        "Rommelmarkten",
        "Speelgoed en spellen",
        "Sport en outdoor",
        "Tickets en Kaartjes",
        "Tuin en Terras",
        "Vastgoedverhuur",
        "Woningverkoop"
    ]

    return categories


def extract_price(price_str):
    """Extract numeric value from price string or return default value."""
    # Search for a pattern that captures a number after the euro symbol
    match = re.search(r'€\s*(\d+)', price_str)
    # If match is found, return the matched number, else return the default value '1'
    return match.group(1) if match else '1'


def delete_items(driver):
    # Navigate to the items page
    driver.get('https://nextdoor.nl/for_sale_and_free/your_items/')

    # Scroll to the end of the page
    scroll_to_end(driver)

    # Find all the three dots icons
    three_dots_icons = driver.find_elements(By.CSS_SELECTOR, ".classified-your-item-caret-menu .dropdown.story-caret-menu.story-moderation-caret-menu.classified-moderation-caret-menu")

    # Iterate over the three dots icons and click the delete button
    for three_dots_icon in three_dots_icons:
        driver.execute_script("arguments[0].scrollIntoView(true);", three_dots_icon)
        driver.execute_script("window.scrollTo(0,100);")
        time.sleep(1)
        print(three_dots_icon.get_attribute('id'))

        three_dots_icon.find_element(By.CSS_SELECTOR, 'button[data-toggle="dropdown"]').click()

        # Wait for the dropdown menu to open
        time.sleep(2)

        # Click the delete button
        delete_button = three_dots_icon.find_element(By.CSS_SELECTOR, 'ul.dropdown-menu li.menuitem:last-child button')
        # driver.execute_script("arguments[0].scrollIntoView(true);", delete_button)
        time.sleep(2)
        delete_button.click()

        # Wait for the confirmation modal to open
        time.sleep(2)

        # Click the confirm button
        confirm_button = driver.find_element(By.CSS_SELECTOR, 'div[role="alertdialog"] button[data-testid="delete-button"]')
        confirm_button.click()
