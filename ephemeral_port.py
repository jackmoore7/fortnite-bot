from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from pyvirtualdisplay import Display
import time as t
import os
import json
import requests
from dotenv import load_dotenv
import requests
from transmission_rpc import Client
load_dotenv()

host = os.getenv("TRANSMISSION_HOST")
port = os.getenv("TRANSMISSION_PORT")
username = os.getenv("TRANSMISSION_USERNAME")
password = os.getenv("TRANSMISSION_PASSWORD")
c = Client(host=host, port=port, username=username, password=password)

def send_webhook(content):
    url = os.getenv('WEBHOOK_URL')
    payload = {
        'content': content
    }
    headers = {'Content-Type': 'application/json'}
    requests.post(url, data=json.dumps(payload), headers=headers)

def port_test():
    if not c.port_test():
        return set_new_port()

def set_new_port():
    try:
        vars = {}
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
        driver.find_element(By.ID, "username").send_keys(str(username))
        driver.find_element(By.ID, "pass").send_keys(str(password))
        driver.find_element(By.ID, "login_button").click()
        driver.find_element(By.ID, "menu-ports").click()
        driver.find_element(By.ID, "pf-eph-btn").click()
        driver.find_element("xpath", '//*[@id="request-port-cont"]/button').click()
        driver.find_element("xpath", '//*[@id="request-port-cont"]/button[2]').click()
        WebDriverWait(driver, 5).until(expected_conditions.visibility_of_element_located((By.XPATH, "//div[@id=\'epf-port-info\']/span")))
        vars["new_port"] = driver.find_element(By.XPATH, "//div[@id=\'epf-port-info\']/span").text
        new_port = "{}".format(vars["new_port"])
    except NoSuchElementException as e:
        send_webhook(f"Element not found: {e}.")
    except TimeoutException as e:
        send_webhook(f"Timed out waiting for element: {e}.")
    except Exception as e:
        send_webhook(f"An unexpected exception occurred: {e}.")
    finally:
        driver.close()
    session = c.get_session()
    old_port = session.peer_port
    c.set_session(peer_port=new_port)
    return f"Port was successfully changed from {old_port} to {new_port}"