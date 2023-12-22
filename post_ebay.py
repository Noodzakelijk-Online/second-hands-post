from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from decouple import config
from nlp_hanlder import get_best_match, get_best_matches
import time
import re
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from post_nextdoor import extract_price

def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView();", element)
    time.sleep(0.5)  # Allow some time for scrolling

def accept_cookies_if_present(driver, timeout=10):
    """Click the accept cookies button if it's present."""
    try:
        # Wait for the cookie acceptance button to be present
        accept_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, 'gdpr-banner-accept'))
        )
        accept_button.click()
        print("Accepted cookies.")
    except TimeoutException:
        # This will be raised if the button is not present after `timeout` seconds
        print("Cookie acceptance modal did not appear.")

def handle_captcha_if_present(driver, timeout=10):
    """Handle the Captcha if it is present"""
    try:
        captcha_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#CentralArea .target-icaptcha-slot')))
        if(captcha_element):
            time.sleep(timeout)
    except:
        time.sleep(0.1)

def handle_sms_if_present(driver, timeout=10):
    """Handle the SMS if it is present"""
    try:
        sms_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, 'smsWithCode')))
        if(sms_element):
            time.sleep(timeout)
    except:
        time.sleep(0.1)

def login_ebay(driver, vault):
    """Login to ebay.nl using credentials from LastPass."""
    website_url = config("EBAY_URL")
    account = next((item for item in vault.accounts if item.url.decode('utf-8') == website_url), None)
    if not account:
        print("ebay account not found in LastPass vault!")
        exit()

    # Open a new tab
    driver.execute_script("window.open('about:blank', 'tab5');")
    driver.switch_to.window("tab5")

    # Navigate to ebay.com
    driver.get(website_url)

    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)

    time.sleep(0.5)
    # Find the login button and click it.
    time.sleep(5)
    # Wait for login page load
    wait = WebDriverWait(driver, 10)
    signin_continue_button = wait.until(EC.presence_of_element_located((By.ID, 'signin-continue-btn')))
    # Find the input fields for email and password. Adjust these selectors if they don't match the website's current design
    email_input = driver.find_element(By.ID, 'userid')
    email_input.send_keys(account.username.decode('utf-8'))
    signin_continue_button.click()

    time.sleep(10)
    handle_captcha_if_present(driver, 10)
    login_button = wait.until(EC.presence_of_element_located((By.ID, 'sgnBt')))
    handle_captcha_if_present(driver, 10)
    password_input = wait.until(EC.element_to_be_clickable((By.ID, 'pass')))
    password_input.send_keys(account.password.decode('utf-8'))
    login_button.click()
    time.sleep(10)

def post_listing_on_ebay(driver, listing):
    """Post a scraped listing to nextdoor.com."""
    # Create a webdriverwait object
    wait = WebDriverWait(driver, 10)

    time.sleep(10)
    handle_sms_if_present(driver, 15)
    post_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.selling-activity a.me-fake-button.fake-btn')))
    # Using JavaScript to scroll to the button
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.2)
    post_button.click()
    time.sleep(2)

    offer_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#TOPINVITATION .section-container__content a.fake-btn')))
    offer_button.click()

    search_suggestion_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.keyword-suggestion__button')))
    driver.find_element(By.CSS_SELECTOR, '.keyword-suggestion .se-search-box input.textbox__control').send_keys(listing["Title"])
    time.sleep(0.2)
    search_suggestion_button.click()
    time.sleep(1)

    # Column modal
    try:
        column_modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.lightbox-dialog .lightbox-dialog__main')))
        time.sleep(1)
        test1 = driver.find_element(By.CSS_SELECTOR, '.lightbox-dialog .category-picker__body')
        test2 = driver.find_element(By.CSS_SELECTOR, '.lightbox-dialog .category-picker__body .se-panel-section')
        # test3 = driver.find_element(By.CSS_SELECTOR, '.lightbox-dialog .category-picker__body .se-panel-section:first-of-type')
        proposed_columns = test2.find_elements(By.CSS_SELECTOR, '.se-field-card')
        proposed_lists = [element.text for element in proposed_columns]
        best_match_index = get_best_match(listing["Category"], proposed_lists)
        if best_match_index < len(proposed_lists):
            proposed_columns[best_match_index].click() # This is because we skipped the first option
        else:
            print(f"Index {best_match_index} is out of range for the available categories.")
            proposed_columns[0].click()
    except:
        print('column_modal didnt appear')



    # Wait for next page
    continue_without_agreement_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.container__content button.prelist-radix__next-action')))
    continue_without_agreement_button.click()
    time.sleep(0.2)

    try:
        # Select condition
        continue_to_offer_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.condition-dialog-radix__continue button.condition-dialog-radix__continue-btn')))
        # tweedehands_radio_button = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='radio'][../span[text()='Tweedehands']]")))
        # tweedehands_radio_button.click()
        radios = driver.find_elements(By.CSS_SELECTOR, '.se-field.condition-picker-radix__radio-group .se-radio-group__option span input[type="radio"]')
        radio_elements = [radio.find_element(By.XPATH, './../..') for radio in radios]
        radio_texts = [e.text.strip() for e in radio_elements]
        try:
            # Finding the index of the radio button with the associated text 'tweedehands'.
            index = radio_texts.index('Tweedehands')
            
            # Clicking the radio button using the found index.
            radios[index].click()
            
        except ValueError:
            print("'tweedehands' not found in radio_texts")

        time.sleep(3)
        continue_to_offer_button.click()
    except TimeoutException:
        print('continue to offer button not displayed')

    # Upload images
    image_paths = listing["Image Paths"]
    absolute_image_paths = "\n".join(os.path.join(os.getcwd(), path) for path in image_paths)
    input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.ebayui-uploader__formContainer input[type="file"]')))
    driver.execute_script('arguments[0].style.visibility= "visible";', input_element)
    time.sleep(1)
    input_element.send_keys(absolute_image_paths)
    time.sleep(5)

    # Description
    desc_iframe_element = driver.find_element(By.CSS_SELECTOR, '.listRte__editorFrame iframe')
    driver.switch_to.frame(desc_iframe_element)
    description_inside_iframe=driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
    description_inside_iframe.send_keys(listing["Description"])
    driver.switch_to.default_content()

    """Required panels"""
    try:
        required_panel = driver.find_element(By.CSS_SELECTOR, '.listGroup[data-key="REQUIRED_GROUP"] .grid[data-key="REQUIRED_ATTRIBUTE_GRID"]')
        if(required_panel.get_attribute('aria-role') == 'none'):
            raise NoSuchElementException 
        required_grid_cells = required_panel.find_elements(By.CSS_SELECTOR, '.grid__cell .grid__cell__wrapper')
        for required_cell in required_grid_cells:
            title = required_cell.find_element(By.CSS_SELECTOR, '.inputField__label label').text
            if(title == 'Objectstaat'):
                continue
            elif(title == 'Merk'):
                select = required_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = required_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_merk = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_merk].click()

            elif(title == 'Type'):
                select = required_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = required_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_type = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_type].click()

            elif(title == 'Compatibel merk'):
                select = required_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = required_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_compatible_brands = get_best_matches(listing["Category"], [e.text for e in popup_lists])
                for bmcb in best_match_compatible_brands:
                    time.sleep(0.3)
                    popup_lists[bmcb].click()
                    time.sleep(0.3)
    except NoSuchElementException:
        print('Required Panel doesnt appeared')
        
    try:
        extra_panel = driver.find_element(By.CSS_SELECTOR, '.listGroup[data-key="RECOMMENDED_GROUP"] .grid[data-key="TOP_ADDITIONAL_ATTRIBUTE_GRID"]')
        if(extra_panel.get_attribute('aria-role') == 'none'):
            raise NoSuchElementException 
        extra_grid_cells = extra_panel.find_elements(By.CSS_SELECTOR, '.grid__cell .grid__cell__wrapper')
        for extra_cell in extra_grid_cells:
            title = extra_cell.find_element(By.CSS_SELECTOR, '.inputField__label label').text
            if(title == 'Thema'):
                select = extra_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = extra_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_thema = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_thema].click()
            elif(title == 'Formaat'):
                select = extra_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = extra_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_formaat = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_formaat].click()

            elif(title == 'Hoogte van het blok'):
                select = extra_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = extra_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_hoogte = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_hoogte].click()

            elif(title == 'Breedte van blok'):
                select = extra_cell.find_element(By.CSS_SELECTOR, '.listInlineSelect__selectBox--button')
                if(select.text != '–'):
                    continue
                scroll_to_element(driver, select)
                time.sleep(0.5)
                select.click()
                time.sleep(0.5)
                popup_lists = extra_cell.find_elements(By.CSS_SELECTOR, '.listInlineSelect__popup .listInlineSelect__menuList ul li.inputField__label')
                best_match_breedte = get_best_match(listing["Category"], [e.text for e in popup_lists])
                popup_lists[best_match_breedte].click()
    except NoSuchElementException:
        print('Extra Panel doesnt appeared')










    # # Brand, model and type
    # brand_element = driver.find_element(By.CSS_SELECTOR, '.listInlineSelect[data-key="requiredAttrList.1"]')
    # model_element = driver.find_element(By.CSS_SELECTOR, '.listInlineSelect[data-key="requiredAttrList.2"]')
    # type_element = driver.find_element(By.CSS_SELECTOR, '.listInlineSelect[data-key="requiredAttrList.3"]')

    # brand_click = brand_element.find_element(By.CSS_SELECTOR, 'button.listInlineSelect__searchBox--button')
    # brand_click.click()
    # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.listInlineSelect_popup')))

    # brand_options = brand_element.find_elements(By.CSS_SELECTOR, '.listInlineSelect_popup .listInlineSelect__customDropdown ul[role="menu"] li.inputField__label')
    # brand_lists = [e.text for e in brand_options]

    # brand_option_indexes = get_best_matches(listing["Category"], brand_lists)
    # for e in brand_option_indexes:
    #     brand_options[e].click()
    #     time.sleep(0.5)


    # Disable Auction
    auction_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-key="auctionSelection"] input[type="checkbox"]')))
    scroll_to_element(driver, auction_element)
    time.sleep(0.5)
    auction_element.click()

    time.sleep(20)
    # Wait for price input box is enabled
    price_input = driver.find_element(By.CSS_SELECTOR, '.listTextInput[data-key="binPrice"] .listTextInput__rightContainer .listTextInput__container input[name="price"]')
    numeric_price = extract_price(listing["Price"])

    price_input.send_keys(int(numeric_price))

    # Select delivery method
    select_delivery_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-key="shippingPrimaryServiceSelectService"]')))
    scroll_to_element(driver, select_delivery_element)
    time.sleep(0.5)
    select_delivery_element.click()

    time.sleep(2)
    standard_delivery_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'label.listShippingServiceSelect__groupContentRow:nth-child(4)')))
    scroll_to_element(driver, standard_delivery_element)
    time.sleep(0.5)
    standard_delivery_element.click()

    # Input 15 on shipping cost
    shipping_cost_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-key="shippingPrimaryServiceCostRate"] input[name="domesticShippingPrice1"]')))
    shipping_cost_input.send_keys(15)

    # International shipping
    intl_shipping_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-key="shippingIntlServiceSelectService"]')))
    intl_shipping_button.click()

    postnl_option = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'label.listShippingServiceSelect__groupContentRow:nth-child(8) input[type="radio"]')))
    postnl_option.click()

    time.sleep(10)
    # Shipping retrieve option enable
    # retrieve_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.inputField[data-key="localPickup"] > input[type="checkbox"]')))
    retrieve_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.inputField[data-key="localPickup"] > label.inputField__label')))
    retrieve_checkbox.click()

    time.sleep(10)
    # International shipping price
    intl_shipping_price_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="intlShippingPrice1"]')))
    intl_shipping_price_input.send_keys(60)

    time.sleep(10)
    # Offer with costs shown button
    offer_with_costs_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-key="listItCallToAction"]')))
    offer_with_costs_button.click()
    time.sleep(3)









def get_ebay_titles(driver):

    # # Navigate to the my postings page
    # driver.get('https://ebay.nl/arnhem/gebruikers/2932588/robert-velhorst')
    # time.sleep(2)
    # Accept cookies if the modal appears
    accept_cookies_if_present(driver)
    # scroll_to_end(driver)
    
    time.sleep(2)
    # Now get all the titles
    titles = [e.text for e in driver.find_elements(By.CSS_SELECTOR, '.item-list h3.item-title a')]
    
    return titles