import os
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from pyvirtualdisplay import Display
from transmission_rpc import Client


def test_port():
    try:
        host = os.getenv("TRANSMISSION_HOST")
        username = os.getenv("TRANSMISSION_USERNAME")
        password = os.getenv("TRANSMISSION_PASSWORD")
        docker_password = os.getenv("DOCKER_PASSWORD")
        port = os.getenv("TRANSMISSION_PORT")
        c = Client(host=host, port=port, username=username, password=password)
        if c.port_test():
            return
        new_port = get_new_port()
        session = c.get_session()
        old_port = session.peer_port
        c.set_session(peer_port=new_port)
        ssh_command = [
            'sshpass', '-p', docker_password, 
            'ssh', f'{username}@{host}', 
            f'echo {str(docker_password)} | sudo -S -p \'\' /usr/local/bin/docker restart haugene-transmission-openvpn1'
        ]

        try:
            subprocess.run(ssh_command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
        return f"Port was changed from {old_port} to {new_port}. Restarting container."
    except Exception as e:
        print(e)

def get_new_port():
    try:
        variables = {}
        display = Display(visible=0, size=(800, 600))
        display.start()
        service = Service(executable_path='/usr/bin/chromedriver')
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        windscribe_username = os.getenv('WINDSCRIBE_USERNAME')
        windscribe_password = os.getenv('WINDSCRIBE_PASSWORD')
        driver = webdriver.Chrome(options=chrome_options, service=service)
        driver.implicitly_wait(10)
        driver.get("https://windscribe.com/login?auth_required#porteph")
        driver.find_element(By.ID, "username").send_keys(str(windscribe_username))
        driver.find_element(By.ID, "pass").send_keys(str(windscribe_password))
        driver.find_element(By.ID, "login_button").click()
        try:
            driver.find_element(By.XPATH, "//button[contains(.,\'Delete Port\')]").click()
        except Exception:
            pass
        driver.find_element(By.XPATH, "//button[contains(.,\'Request Matching Port\')]").click()
        WebDriverWait(driver, 5).until(expected_conditions.visibility_of_element_located((By.XPATH, "//div[@id=\'epf-port-info\']/span")))
        variables["new_port"] = driver.find_element(By.XPATH, "//div[@id=\'epf-port-info\']/span").text
        new_port = "{}".format(variables["new_port"])
        return int(new_port)
    except NoSuchElementException as e:
        print(f"Element not found: {e}.")
    except TimeoutException as e:
        print(f"Timed out waiting for element: {e}.")
    except Exception as e:
        print(f"An unexpected exception occurred: {e}.")
    finally:
        driver.close()