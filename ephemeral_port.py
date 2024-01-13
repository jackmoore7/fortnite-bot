from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from pyvirtualdisplay import Display
import time as t
import os
import json
import requests

def send_webhook(content):
    url = os.getenv('WEBHOOK_URL')
    payload = {
        'content': content
    }
    headers = {'Content-Type': 'application/json'}
    requests.post(url, data=json.dumps(payload), headers=headers)

def get_new_port():
    try:
        display = Display(visible=0, size=(800, 600))
        display.start()
        service = Service(executable_path='/usr/lib/chromium-browser/chromedriver')
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        username = os.getenv('WINDSCRIBE_USERNAME')
        password = os.getenv('WINDSCRIBE_PASSWORD')
        driver = webdriver.Chrome(options=chrome_options, service=service)
        driver.implicitly_wait(10)
        driver.get('https://www.windscribe.com/login')
        send_webhook("Logging into Windscribe")
        driver.find_element(By.ID, "username").send_keys(str(username))
        driver.find_element(By.ID, "pass").send_keys(str(password))
        driver.find_element(By.ID, "login_button").click()
        send_webhook("Logged in")
        driver.find_element(By.ID, "menu-ports").click()
        driver.find_element(By.ID, "pf-eph-btn").click()
        driver.find_element("xpath", '//*[@id="request-port-cont"]/button').click()
        send_webhook("Deleted existing port")
        driver.find_element("xpath", '//*[@id="request-port-cont"]/button[2]').click()
        send_webhook("Requested new matching port")
        port = driver.find_element("xpath", '//*[@id="epf-port-info"]/span[1]')
        print(port)
        send_webhook(f"New port requested successfully: {port.text}")
    except NoSuchElementException as e:
        send_webhook(f"Element not found: {e}. Trying again in 1 hour.")
        t.sleep(3600)
        get_new_port()
    except TimeoutException as e:
        send_webhook(f"Timed out waiting for element: {e}. Trying again in 1 hour.")
        t.sleep(3600)
        get_new_port()
    except Exception as e:
        send_webhook(f"An unexpected exception occurred: {e}. Trying again in 1 hour.")
        t.sleep(3600)
        get_new_port()
    finally:
        driver.close()