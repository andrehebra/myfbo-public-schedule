from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
from ics import Calendar, Event
import os
from datetime import datetime
from datetime import datetime
import pytz
import re

from dotenv import load_dotenv


load_dotenv()

USERNAME = os.getenv("MYFBO_USERNAME")
PASSWORD = os.getenv("MYFBO_PASSWORD")

calendar_list = []
def save_calendars_by_staff(calendar_list, output_dir="staff_calendars", timezone_str="America/New_York"):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    tz = pytz.timezone(timezone_str)
    default_location = "391 Herndon Ave Suite A, Orlando, FL 32803"

    # Group flights by flight_staff
    staff_dict = {}
    for flight in calendar_list:
        staff = flight.get("flight_staff", "unknown").strip().replace(" ", "_").lower()
        staff_dict.setdefault(staff, []).append(flight)

    # Generate and save .ics files
    for staff, flights in staff_dict.items():
        calendar = Calendar()

        for flight in flights:
            event = Event()
            event.name = flight.get("title", "Flight")  # Use 'title' if available

            try:
                start_dt_naive = datetime.strptime(flight.get("from_time"), "%m/%d/%y %H:%M")
                end_dt_naive = datetime.strptime(flight.get("to_time"), "%m/%d/%y %H:%M")

                start_dt = tz.localize(start_dt_naive)
                end_dt = tz.localize(end_dt_naive)

                event.begin = start_dt
                event.end = end_dt
            except Exception as e:
                print(f"Skipping event due to bad date format: {e}")
                continue

            event.description = flight.get("equipment", "")
            event.location = flight.get("location") or default_location

            calendar.events.add(event)

        file_path = os.path.join(output_dir, f"{staff}.ics")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(calendar))

    print(f"ICS files saved to '{output_dir}'")



def parse_schedule_card(card_html):
    soup = BeautifulSoup(card_html, "html.parser")
    
    table = soup.find("table", class_="sd")
    rows = table.find_all("tr")

    flight_data = {
        "flight_staff": None,
        "from_time": None,
        "to_time": None,
        "equipment": None,
        "flight_id": None,
        "title": None,
        "location": "391 Herndon Ave Suite A, Orlando, FL 32803"  # default location
    }

    # Parse title from bold tag (if present)
    bold_tag = soup.find("b")
    if bold_tag and "Rental Reservation for" in bold_tag.text:
        match = re.search(r"Rental Reservation for (.+?) at", bold_tag.text)
        if match:
            name = match.group(1)
            flight_data["title"] = f"Reservation with {name}"
        else:
            flight_data["title"] = "Reservation"

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue

        label = cells[0].get_text(strip=True)

        if "Time:" in label and len(cells) >= 5:
            flight_data["from_time"] = cells[3].get_text(strip=True)
            flight_data["to_time"] = cells[4].get_text(strip=True)

        elif "Equipment:" in label:
            flight_data["equipment"] = cells[1].get_text(strip=True) if len(cells) > 1 else None

        elif "Flight Staff:" in label:
            flight_data["flight_staff"] = cells[1].get_text(strip=True)

        elif "Flight" in cells[-1].text:
            flight_data["flight_id"] = cells[-1].get_text(strip=True)

    calendar_list.append(flight_data)
    print(flight_data)
    return flight_data


def remove_duplicate_flights(calendar_list):
    seen_ids = set()
    unique_flights = []

    for flight in calendar_list:
        flight_id = flight.get("flight_id")
        if flight_id and flight_id not in seen_ids:
            unique_flights.append(flight)
            seen_ids.add(flight_id)

    return unique_flights


# Start browser
driver = webdriver.Chrome()

# Go to the top-level page with <frameset>
driver.get("https://prod.myfbo.com/link.asp?fbo=aoal")

try:
    # Wait for and switch to the login frame ("myfbo2")
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "myfbo2"))
    )

    # Now find and fill the email input inside that frame
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "email"))
    )
    email_input.send_keys(USERNAME)
    print("✅ Email entered!")

    # input password
    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "password"))
    )
    password_input.send_keys(PASSWORD)


    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, "gogo"))
    )
    login_button.click()

    ### --- AFTER LOGIN--- ###
    # navigate to home page
    time.sleep(5)  # Wait for the page to load after login

    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "tf"))
    )

    wait = WebDriverWait(driver, 10)
    home_tab = wait.until(EC.element_to_be_clickable((By.ID, "SchedRpt")))
    home_tab.click()

    # navigate to my schedule page
    driver.switch_to.parent_frame()  # Switch back to the main content
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "wa"))
    )

    my_schedule = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@onclick, \"pnm.oPen('../r/list_day_sched.asp?list_date=\")]")))

    my_schedule.click()

    # get information from the table
    ccrd_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ccrs")))

    main_window = driver.current_window_handle

    #### loop through each schedule page and click on each CCRD element
    card_html_list = []

    for j in range(len(ccrd_elements) - 1):
        print(j)
        ccrd_elements[j].click()

        # Wait for the popup to load (class 'sd' inside a table)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sd")))
        # Get the outerHTML of the card container
        schedule_card = driver.find_element(By.CLASS_NAME, "sd")
        card_html = schedule_card.get_attribute("outerHTML")
        card_html_list.append(card_html)
        print(card_html)

        title_card = driver.find_element(By.ID, "showDetail")
        card_html += title_card.get_attribute("outerHTML")

        parse_schedule_card(card_html)
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//td[contains(text(), 'Close') and contains(@onclick, 'setCover')]"))
        )
        close_button.click()
    for i in range(10):
        driver.switch_to.parent_frame()  # Switch back to the main content
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "tf"))
        )


        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@onclick, "hNext.value")]'))
        )
        next_button.click()

        driver.switch_to.parent_frame()  # Switch back to the main content
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "wa"))
        )

        
        ccrd_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ccrs")))
        ccrd_elements = driver.find_elements(By.CLASS_NAME, "ccrd")

        for j in range(len(ccrd_elements) - 1):

            ccrd_elements[j].click()

            # Wait for the popup to load (class 'sd' inside a table)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sd")))
            # Get the outerHTML of the card container
            schedule_card = driver.find_element(By.CLASS_NAME, "sd")
            card_html = schedule_card.get_attribute("outerHTML")
            card_html_list.append(card_html)

            
            title_card = driver.find_element(By.ID, "showDetail")
            card_html += title_card.get_attribute("outerHTML")


            parse_schedule_card(card_html)

            

            close_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//td[contains(text(), 'Close') and contains(@onclick, 'setCover')]"))
            )
            close_button.click()

    calendar_list = remove_duplicate_flights(calendar_list)
    save_calendars_by_staff(calendar_list, output_dir="docs")


    time.sleep(5)  # Watch it work

except Exception as e:
    print("❌ Something went wrong:", e)

finally:
    driver.quit()

