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
from dateutil.relativedelta import relativedelta
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from dotenv import load_dotenv


load_dotenv()

USERNAME = os.getenv("MYFBO_USERNAME")
PASSWORD = os.getenv("MYFBO_PASSWORD")

calendar_list = []

def parse_reservations_from_table(reservation_table):
    rows = reservation_table.find("tbody").find_all("tr")
    reservations = []
    i = 0

    while i < len(rows):
        row = rows[i]
        cells = row.find_all("td")

        # Initialize flight data
        flight = {
            "from_time": None,
            "to_time": None,
            "equipment": None,
            "flight_staff": None,
            "student": None,
            "type": None,
            "base": None,
            "remark": None,
            "title": None,
        }

        # Parse main (first) row
        flight["from_time"] = cells[1].get_text(strip=True)
        flight["to_time"] = cells[2].get_text(strip=True)
        flight["equipment"] = cells[4].get_text(strip=True)
        flight["student"] = cells[5].get_text(strip=True)
        flight["type"] = cells[6].get_text(strip=True)
        flight["base"] = cells[7].get_text(strip=True)

        # Try to get remark from title attribute of image (if present)
        remark_img = cells[9].find("img") if len(cells) > 9 else None
        if remark_img and remark_img.has_attr("title"):
            flight["remark"] = remark_img["title"]

        # Handle possible second row (with only pilot info)
        if i + 1 < len(rows):
            next_row = rows[i + 1]
            next_cells = next_row.find_all("td")

            # If the first cell is just a dash or empty, assume it's the continuation
            if next_cells[0].get_text(strip=True) in ["", "–", "-"]:
                flight_staff = next_cells[4].get_text(strip=True)

                # Check for an <img> with a title in that same cell
                staff_img = next_cells[4].find("img")
                if staff_img and staff_img.has_attr("title"):
                    flight_staff += f" ({staff_img['title'].strip()})"

                flight["flight_staff"] = flight_staff
                i += 1  # Skip the second row
            else:
                # Otherwise treat this as a single-row reservation
                flight["flight_staff"] = flight["equipment"]
                flight["equipment"] = None
        else:
            flight["flight_staff"] = flight["equipment"]
            flight["equipment"] = None

        # Create a nice title
        if flight["student"] and flight["flight_staff"]:
            flight["title"] = f"Reservation with {flight['student']} and {flight['flight_staff']}"
        elif flight["student"]:
            flight["title"] = f"Reservation with {flight['student']}"
        else:
            flight["title"] = "Flight Reservation"

        reservations.append(flight)
        i += 1

    calendar_list.extend(reservations)
    return reservations


import os
import re
from datetime import datetime
import pytz
from ics import Calendar, Event

def save_calendars_by_staff(calendar_list, output_dir="staff_calendars", timezone_str="America/New_York"):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    tz = pytz.timezone(timezone_str)
    default_location = "391 Herndon Ave Suite A, Orlando, FL 32803"

    # Group flights by flight_staff
    staff_dict = {}
    for flight in calendar_list:
        staff = (flight.get("flight_staff") or "unknown").strip().replace(" ", "_").lower()
        staff_dict.setdefault(staff, []).append(flight)

    # Generate and save .ics files
    for staff, flights in staff_dict.items():
        calendar = Calendar()

        for flight in flights:
            event = Event()
            event.name = flight.get("title", "Flight")

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

            # Build the description
            description_parts = []
            equipment = flight.get("equipment")
            remark = flight.get("remark")

            if equipment:
                description_parts.append(equipment)
            if remark:
                description_parts.append(f"\n{remark}")

            event.description = "\n".join(description_parts)
            event.location = flight.get("location") or default_location

            calendar.events.add(event)

        # Clean up staff name for filename
        safe_staff = re.sub(r"\s+", "", str(staff))
        file_path = os.path.join(output_dir, f"{safe_staff}.ics")

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

        print(flight_data)
    calendar_list.append(flight_data)
    # print(flight_data)
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

def getTable():
    html = driver.page_source  # or however you're getting the HTML
    soup = BeautifulSoup(html, "html.parser")

    reservation_table = soup.find("table", id="TABLE_1")

    reservations = parse_reservations_from_table(reservation_table)
    # print(reservations)

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
    driver.switch_to.parent_frame()  
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "wa"))
    )

    my_schedule = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id=\"mainbody\"]/div/div/fieldset[3]/div/button[1]")))

    my_schedule.click()

    # time.sleep(5)  # Wait for the schedule page to load --> WE ARE AT THE RESERVATINOS LIST MENU NOW

    ### --- ON RESERVATIONS LIST PAGE --- ###

    # input date from
    date_input = wait.until(EC.presence_of_element_located((By.NAME, "dfr")))

    # Format today's date as MM/DD/YY
    today_str = datetime.now().strftime("%m/%d/%y")

    # Clear and input the date
    date_input.clear()
    date_input.send_keys(today_str)

    date_input = wait.until(EC.presence_of_element_located((By.NAME, "dto")))

    one_month_later = (datetime.now() + relativedelta(months=1)).strftime("%m/%d/%y")

    # Clear and input the date
    date_input.clear()
    date_input.send_keys(one_month_later)

    # select KORL from dropdown
    # Locate the dropdown element (replace with your actual locator if needed)
    dropdown = Select(driver.find_element(By.NAME, "apt"))

    # Select the option with value "KORL"
    dropdown.select_by_value("KORL")

    # click on the button to show date table
    button = driver.find_element(By.XPATH, "//input[@onclick=\"actGo('all_schedule.asp?order=1&tor=F');\"]")
    button.click()

    time.sleep(3)

    ### --- ON TABLE PAGE --- ###
    hasNextPage = True
    driver.switch_to.parent_frame()  # Switch back to the main content
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "tf"))
    )
    try:
        element = driver.find_element(By.XPATH, "//a[contains(@onclick, 'disablePrevNext()') and contains(@onclick, 'hNext.value')]")
        hasNextPage = True
    except NoSuchElementException:
        hasNextPage = False
    driver.switch_to.parent_frame()  # Switch back to the main content
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "wa"))
    )
    getTable()
    while hasNextPage:
        driver.switch_to.parent_frame()  # Switch back to the main content
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "tf"))
        )
        try:
            element = driver.find_element(By.XPATH, "//a[contains(@onclick, 'disablePrevNext()') and contains(@onclick, 'hNext.value')]")
            element.click()
            hasNextPage = True
        except:
            hasNextPage = False
        driver.switch_to.parent_frame()  # Switch back to the main content
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "wa"))
        )
        getTable()


    time.sleep(5)
    # calendar_list = remove_duplicate_flights(calendar_list)
    save_calendars_by_staff(calendar_list, output_dir="docs")


    time.sleep(5)  # Watch it work

except Exception as e:
    print("❌ Something went wrong:", e)

finally:
    driver.quit()

