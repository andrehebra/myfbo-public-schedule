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

from dotenv import load_dotenv

# old code from other scheduling page
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