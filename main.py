from decouple import config
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from post_nextdoor import login_nextdoor, post_listing_on_nextdoor, delete_items, get_all_titles
from markplaats import login_markplaats, post_listing_on_marktplaats, get_markplaats_titles
from post_koopplein import login_koopplein, post_listing_on_koopplein, get_koopplein_titles
from post_ebay import login_ebay, post_listing_on_ebay, get_ebay_titles
import time
import re
import lastpass
import csv
import requests
import os
import string

def sanitize_filename(filename):
    """Sanitize the filename by removing special characters and spaces."""
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    regex = re.compile(r"[^{}]+".format(valid_chars))
    return regex.sub("", filename).strip()

def download_image(url, item_name):
    """Downloads an image given a URL and saves it in the specified folder."""
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Extract the file name from the URL, splitting at '?' to remove query parameters
    file_name_from_url = url.split('/')[-1].split('?')[0]
    
    # Sanitize the filenames
    safe_item_name = sanitize_filename(item_name)
    safe_file_name_from_url = sanitize_filename(file_name_from_url)

    # Construct directory path: images/item_name/
    directory_path = os.path.join("images", safe_item_name)

    # Check if the directory exists, if not, create it
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # Construct the full path where the image will be saved
    file_name = os.path.join(directory_path, safe_file_name_from_url)

    with open(file_name, 'wb') as file:
        for chunk in response.iter_content(8192):
            file.write(chunk)

    return file_name

def setup_lastpass():
    # Load email and password from .env file
    LASTPASS_EMAIL = config('LASTPASS_EMAIL')
    LASTPASS_PASSWORD = config('LASTPASS_PASSWORD')
    # Setup lastpass
    vault = lastpass.Vault.open_remote(LASTPASS_EMAIL, LASTPASS_PASSWORD)
    return vault

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # To suppress the log itself
    chrome_options.add_argument('--disable-usb-discovery')  # Disables USB device discovery
    chrome_options.add_argument('--log-level=3')

    chrome_driver_path = config('CHROME_DRIVER_PATH')

    # Create a Service object
    service = Service(chrome_driver_path)
    # Create a Chrome webdriver instance
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

def login_tweedehands(driver, vault):
    account = next((item for item in vault.accounts if item.url.decode('utf-8') == 'https://www.tweedehands.net/login.php'), None)
    if account:
        username = account.username.decode('utf-8')
        password = account.password.decode('utf-8')
        # print("User name is ", username, ", Password is ", password)
    else:
        print("Account not found in LastPass vault!")
        exit()
        
    # Navigate to the website
    driver.get("https://www.tweedehands.net/login.php")

    # Find the input fields for username and password. 
    username_input = driver.find_element(By.ID, 'usrname')  # Replace 'username' with the correct ID or name
    password_input = driver.find_element(By.ID, 'passwd')  # Replace 'password' with the correct ID or name

    # Type into the input fields
    username_input.send_keys(username)
    password_input.send_keys(password)

    # Find and click the login button
    login_button = driver.find_element(By.CSS_SELECTOR, '#login .primaryAction')
    login_button.click()

def scrape_tweedehands(driver):
    # time.sleep(200)
    base_url = 'https://www.tweedehands.net/mijnadvertentielijst.php'

    # Now, navigate to the new URL (my ads)
    driver.get(base_url)
    try:
        consent_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.fc-button.fc-cta-consent.fc-primary-button')))
        consent_button.click()
    except TimeoutException:
        print("Consent button was not found or not clickable. Please adjust the selector. Go to next step")
        # driver.quit()
        # exit() # Stop the script

    # This list will stroe all the URLs from all pages
    all_links = []

    while True:
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#rightCntr .normalpage > h1')))

        # Extract the href attributes from the current page
        elements = driver.find_elements(By.CSS_SELECTOR, '#rightCntr .normalpage ul.wide.admin li .text h3 a')
        links = [element.get_attribute('href') for element in elements]
        all_links.extend(links)

        # Check if there's a "next page" link or button
        try:
            next_page_element = driver.find_element(By.ID, 'volgende')  # Adjust the selector as needed
            driver.execute_script("arguments[0].scrollIntoView(true);", next_page_element)
            next_page_element.click()
        except NoSuchElementException:
            # If the "next page" button doesn't exist, break out of the loop
            print("No such element with id volgende exists")
            break
        except StaleElementReferenceException:
            time.sleep(1)
            continue
    # List to store the scraped data in csv file
    data_list = []
    # Will be returned from this function directly
    data_list_for_return=[]
    # Create/Open the CSV file and write the header first
    with open('scraped_data.csv', 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["Link", "Title", "Category", "Tag", "Description", "Price", "Image Paths"])
        writer.writeheader()
    # Print out the links
    for link in all_links:
        print(link)
        driver.get(link)

        time.sleep(5)
        try:
            # Waits for up to 10 seconds until the itle is located
            title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#rightCntr .detailBox .left h1')))

            raw_title = title_element.text

            matches = re.findall(r'[^()]+(?![^(]*\))', raw_title)

            title = ''.join(matches)

            try:
                tag = driver.find_element(By.CSS_SELECTOR, '#rightCntr .kenmerk').text
            except NoSuchElementException:
                tag=""    

            category = driver.find_element(By.CSS_SELECTOR, '#breadcrumbs li:nth-child(2) a').text
            raw_price = driver.find_element(By.CSS_SELECTOR, '#rightCntr .detailBox .left .prijs').text
            price = raw_price.split(':')[1].strip() if ':' in raw_price else raw_price
            description = driver.find_element(By.CSS_SELECTOR, '#rightCntr .detailBox .left .omschrijving').text


            # First, locate the container of the 'omschrijving' which contains all <p> tags
            container = driver.find_element(By.CSS_SELECTOR, '#rightCntr .detailBox .left .omschrijving')

            # Find the <p> tag with the specific style
            specific_p_tag = None
            try:
                specific_p_tag = container.find_element(By.CSS_SELECTOR, 'p[style="margin-top: 10px;"]')
            except:
                pass

            # If the specific <p> tag is found, extract texts from preceding <p> tags
            if specific_p_tag:
                preceding_p_tags = driver.execute_script("""
                var element = arguments[0];
                var previousSiblings = [];
                while (element.previousElementSibling) {
                    element = element.previousElementSibling;
                    if (element.tagName.toLowerCase() === 'p') {
                        previousSiblings.unshift(element);
                    }
                }
                return previousSiblings;
                """, specific_p_tag)

                # Extract text from preceding <p> tags
                descriptions = [p.text for p in preceding_p_tags]
                print(descriptions)

            description = '\n'.join(descriptions)

            if not specific_p_tag:
                description = driver.find_element(By.CSS_SELECTOR, '#rightCntr .detailBox .left .omschrijving').text

            img_elements = driver.find_elements(By.CSS_SELECTOR, '.right .pic .foto ul li a')

            if not img_elements: # if no multiple images found
                # Try getting the big image element
                big_img_element = driver.find_element(By.CSS_SELECTOR, '.right .pic .foto #ad_img_links a')
                img_urls = [big_img_element.get_attribute('href')]
            else:
                img_urls = [img.get_attribute('href') for img in img_elements]

            # Download the images and save their paths
            downloaded_image_paths = [download_image(img_url, title) for img_url in img_urls]

            # Store the scraped data in a dictionary
            data = {
                "Link": link,
                "Title": title,
                "Category": category,
                "Tag": tag,
                "Description": description,
                "Price": price,
                "Image Paths": ','.join(downloaded_image_paths)
            }
            data_return = {
                "Link": link,
                "Title": title,
                "Category": category,
                "Tag": tag,
                "Description": description,
                "Price": price,
                "Image Paths": downloaded_image_paths
            }

            # Append the dictionary to your list
            data_list.append(data)
            data_list_for_return.append(data_return)
            # Append the scraped data immediately to the CSV
            with open('scraped_data.csv', 'a', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["Link", "Title", "Category", "Tag", "Description", "Price", "Image Paths"])
                writer.writerow(data)        
        
        except (NoSuchElementException, TimeoutException):
            print(f"Failed to scrape data for link: {link}")
            continue

    return data_list_for_return          

def get_saved_data():
    # Now, we will load the data_list from the scraped_data.csv file
    data_list = []
    with open('scraped_data.csv', 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Convert the "Image Paths" string back to a list
            row["Image Paths"] = row["Image Paths"].split(',')
            data_list.append(row)
    return data_list

# Function to normalize strings
def normalize_string(s):
    return ' '.join(s.split())

driver=setup_driver()
driver.maximize_window()

vault = setup_lastpass()
# Waits for up to 10 seconds
wait = WebDriverWait(driver, 30)
# Maximize the browser window

if config('SCRAPED_STATUS').lower() == 'true':
    data_list = get_saved_data()
    












else:
    login_tweedehands(driver, vault)
    data_list = scrape_tweedehands(driver)
print(len(data_list))

# ######### NextDoor ############
# # Login to nextdoor.com
# login_nextdoor(driver, vault)
# time.sleep(10)
# # Get already posted listings
# titles = get_all_titles(driver)
# # For each scraped listing, attempt to post it on nextdoor.com
# for item in data_list:
#     normalized_title = normalize_string(item["Title"])
#     if normalized_title in (normalize_string(title) for title in titles):
#         continue
#     post_listing_on_nextdoor(driver, item)
# # delete_items(driver)


# ########## Marktplaats ############
# login_markplaats(driver, vault)
# time.sleep(5)
# titles = get_markplaats_titles(driver)
# for item in data_list:
#     normalized_title = normalize_string(item["Title"])
#     if normalized_title in (normalize_string(title) for title in titles):
#         continue
#     if post_listing_on_marktplaats(driver, item):
#         continue
#     else:
#         break

# driver.close()


########## Koopplein ############
login_koopplein(driver, vault)
time.sleep(5)
titles = get_koopplein_titles(driver)
for item in data_list:
    normalized_title = normalize_string(item["Title"])
    if normalized_title in (normalize_string(title) for title in titles):
        continue
    post_listing_on_koopplein(driver, item)

driver.close()


######### Ebay ############
login_ebay(driver, vault)
time.sleep(5)
titles = get_ebay_titles(driver)
for item in data_list:
    normalized_title = normalize_string(item["Title"])
    if normalized_title in (normalize_string(title) for title in titles):
        continue
    post_listing_on_ebay(driver, item)

driver.close()