import pprint
import logging
import json
import os
import time
from utils import *
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from mailjet_rest import Client
from dotenv import load_dotenv
load_dotenv()
pp = pprint.PrettyPrinter(indent=2)

MANUAL_LOGIN = True
DEBUG_MODE = False
CHANGE_MODE = True
CLICK_DELAY = 5 # seconds

# These stations and ports don't work
EXCLUDE_FRONT = [(52957, 1), (52958, 1)]
EXCLUDE_BACK = []

LOGGING_SUPERINFO_LEVEL = logging.INFO + 5
logging.addLevelName(LOGGING_SUPERINFO_LEVEL, "SUPERINFO")

def superinfo(self, message, *args, **kws):
  if self.isEnabledFor(LOGGING_SUPERINFO_LEVEL):
    self._log(LOGGING_SUPERINFO_LEVEL, message, args, **kws)

logging.Logger.superinfo = superinfo
LOGGING_FORMAT = '[%(levelname).1s%(asctime)s %(filename)s:%(lineno)d] %(message)s'

if DEBUG_MODE:
  logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
else:
  logging.basicConfig(format=LOGGING_FORMAT, level=LOGGING_SUPERINFO_LEVEL)

logger = logging.getLogger()

def setup():
  logger.superinfo("Getting browser...") 
  # Create Chromeoptions instance 
  options = webdriver.ChromeOptions() 
  
  options.add_argument("--incognito")
  
  options.add_argument("--ignore-certificate-errors")
  
  options.add_argument("--remote-allow-origins=*")
  
  # Adding argument to disable the AutomationControlled flag 
  options.add_argument("--disable-blink-features=AutomationControlled") 
  
  # Exclude the collection of enable-automation switches 
  options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
  
  # Turn-off userAutomationExtension 
  options.add_experimental_option("useAutomationExtension", False) 
  
  # Setting the driver path and requesting a page 
  driver = webdriver.Chrome(options=options) 
  
  # Changing the property of the navigator value for webdriver to undefined 
  driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") 

  # Limitation: during login, must have browser window open on screen (not necessarily selected)
  # TODO: enable headless mode:
  # options = webdriver.ChromeOptions()
  # options.headless = True
  # driver = webdriver.Chrome(options=options)

  logger.superinfo("Opening website...")
  driver.get("https://sky.shellrecharge.com/evowner/account/sign-in")

  while not driver.find_elements(value="mat-input-1"):
    continue

  logger.superinfo("Entering info...")
  email_txtbx = driver.find_element(value="mat-input-0")
  email_txtbx.send_keys(os.environ['GREENSHELL_USERNAME'])
  pw_txtbx = driver.find_element(value="mat-input-1")
  pw_txtbx.send_keys(os.environ['GREENSHELL_PASSWORD'])
  
  if not MANUAL_LOGIN:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # find iframe
    captcha_iframe = WebDriverWait(driver, 2).until(
        ec.presence_of_element_located(
            (
                By.TAG_NAME, 'iframe'
            )
        )
    )

    ActionChains(driver).move_to_element(captcha_iframe).click().perform()

    captcha_box = WebDriverWait(driver, 2).until(
        ec.presence_of_element_located(
            (
                By.ID, 'g-recaptcha-response'
            )
        )
    )

    driver.execute_script("arguments[0].click()", captcha_box)
    logger.superinfo('I am not a robot I swear!')

    # Do the audio challenge for captcha
    captcha_ok = False
    audio_sent = False

    while not captcha_ok:
      driver.switch_to.frame(captcha_iframe)
      holder = driver.find_element(by=By.CLASS_NAME, value='rc-anchor-checkbox-holder')
      span = holder.find_element(by=By.TAG_NAME, value='span')

      if "recaptcha-checkbox-checked" in span.get_attribute("class"):
        captcha_ok = True
        logger.superinfo("Got u good lmao")
      elif not audio_sent:
        driver.switch_to.default_content()
        iframe = driver.find_element(
            by=By.XPATH, value="//iframe[@title='recaptcha challenge expires in two minutes']")
        driver.switch_to.frame(iframe)
        audio_button_list = driver.find_elements(by=By.ID, value='recaptcha-audio-button')
        if audio_button_list:
          logger.superinfo("Audio button found")
          driver.execute_script("arguments[0].click()", audio_button_list[0])
          while not driver.find_elements(by=By.CLASS_NAME, value="rc-audiochallenge-tdownload-link"):
            continue
          audio_link_div = driver.find_element(
              by=By.XPATH, value="//a[@class='rc-audiochallenge-tdownload-link']")
          audio_link = audio_link_div.get_attribute('href')
          audio = get_challenge_audio(audio_link)
          audio_output = speech_to_text(audio)
          driver.find_element(by=By.ID, value='audio-response').send_keys(audio_output)
          driver.find_element(by=By.ID, value='recaptcha-verify-button').click()
          audio_sent = True
      driver.switch_to.default_content()

    can_login = False

    while not can_login:
      # find the login button
      login = driver.find_element(
        by=By.CLASS_NAME, value="green_btn_lg.customize-primary-bg.mat-button")
      can_login = (login.get_attribute("disabled") != 'true')

    # clicking on the button
    time.sleep(CLICK_DELAY)
    login.click()

  logger.superinfo("Logging in...")
  while driver.find_elements(value="mat-input-1"):
    continue
  logger.superinfo("Logged in!")

  return driver


def read_station(driver):
  output_dict = dict()
  html = BeautifulSoup(driver.page_source, features="lxml")
  for card in html.body.find_all('mat-card', attrs={"class": "notify_list"}):
    station_id = int(
        card.find('div', attrs={"class": "charger-detail-head"}).span.text.split(':')[-1])
    output_dict.setdefault(station_id, dict())
    chargers = card.find('div', attrs={"class": "charger-detail-body"}
                         ).find_all('div', attrs={"class": "charger_info"})
    for charger in chargers:
      charger_num = int(charger.find('div', attrs={"class": "number_charge"}).span.text)
      charger_avail = charger.find(
          'div', attrs={"class": "available_info"}).span.text.lstrip('(').rstrip(')')
      output_dict[int(station_id)][int(charger_num)] = charger_avail
  return output_dict


def get_front_and_back(driver):
  logger.superinfo("Checking stations...")
  try:
    time.sleep(CLICK_DELAY)
    driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
    while not any([el.text == "521407_4100 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
      continue
    back_spots = [el for el in driver.find_elements(
        by=By.TAG_NAME, value="a") if el.text == "521407_4100 Bayside"][0]
    time.sleep(CLICK_DELAY)
    back_spots.click()
    while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
      continue

    back_availabilities = read_station(driver)
    logger.info("Looked at the back")
    logger.info(json.dumps(back_availabilities, indent=2))
    time.sleep(CLICK_DELAY)
    driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
    while not any([el.text == "521412_4000 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
      continue
    logger.info("Looking at the front")
    front_spots = [el for el in driver.find_elements(
        by=By.TAG_NAME, value="a") if el.text == "521412_4000 Bayside"][0]
    time.sleep(CLICK_DELAY)
    front_spots.click()
    while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
      continue
    front_availabilities = read_station(driver)
    logger.info("Looked at the front")
    logger.info(json.dumps(front_availabilities, indent=2))
  except:
    return None, None

  return front_availabilities, back_availabilities


def handle_excludes(front_availabilities, back_availabilities):
  # Yeet the ones that are reserved / don't work
  for exc_station, port in EXCLUDE_FRONT:
    front_availabilities[exc_station].pop(port)
  for exc_station, port in EXCLUDE_BACK:
    back_availabilities[exc_station].pop(port)
  to_delete_front = [station for station, port in front_availabilities.items() if port == dict()]
  to_delete_back = [station for station, port in back_availabilities.items() if port == dict()]
  for station in to_delete_front:
    front_availabilities.pop(station)
  for station in to_delete_back:
    back_availabilities.pop(station)
  return front_availabilities, back_availabilities


def send_email():
  api_key = os.environ['API_KEY']
  api_secret = os.environ['API_SECRET']
  email_segments = []
  email_segments.append(f"Charger found in the {' AND '.join(available_location)}!")
  email_segments.append(f"Front: {front_num_available}/{front_total}")
  email_segments.extend([f"{k}\t{v}" for k, v in front_availabilities.items()])
  email_segments.append(f"\nBack: {back_num_available}/{back_total}")
  email_segments.extend([f"{k}\t{v}" for k, v in back_availabilities.items()])
  email_text = "\n".join(email_segments)
  logger.superinfo(email_text)

  mailjet = Client(auth=(api_key, api_secret), version='v3.1')
  data = {
      'Messages': [
          {
              "From": {
                  "Email": os.environ['MY_EMAIL'],
                  "Name": "George"
              },
              "To": [
                  {
                      "Email": os.environ['MY_EMAIL'],
                      "Name": "George"
                  }
              ],
              "Subject": "EV Charger Availabilities",
              "TextPart": f"{email_text}"
          }
      ]
  }
  if not DEBUG_MODE:
    result = mailjet.send.create(data=data)
    logger.info(f"Sent API Response: {json.dumps(result.json(), indent=2)}")
    if result.status_code == 200:
      logger.superinfo("Email sent successfully!")

if __name__ == '__main__':
  driver = setup()
  front_availabilities_prev, back_availabilities_prev = None, None
  while True:
    try:
      front_availabilities, back_availabilities = get_front_and_back(driver)
      if (front_availabilities, back_availabilities) == (None, None):
        continue
      front_availabilities, back_availabilities = handle_excludes(
          front_availabilities, back_availabilities)

      front_total = sum(len(v) for v in front_availabilities.values())
      front_num_available = sum(vv == 'Available' for v in front_availabilities.values()
                                for vv in v.values())
      
      back_total = sum(len(v) for v in back_availabilities.values())
      back_num_available = sum(vv == 'Available' for v in back_availabilities.values()
                               for vv in v.values())

      if back_availabilities_prev is None and front_availabilities_prev is None:
        front_availabilities_prev, back_availabilities_prev = front_availabilities, back_availabilities
      
      available_location = []
      if CHANGE_MODE:
        will_send_email = False
        if front_availabilities_prev != front_availabilities or back_availabilities_prev != back_availabilities:
          for station, ports in front_availabilities.items():
            if any(ports[port] == "Available" and front_availabilities_prev[station][port] != "Available" for port in ports):
              available_location.append("FRONT")
              will_send_email = True
              break
          for station, ports in back_availabilities.items():
            if any(ports[port] == "Available" and back_availabilities_prev[station][port] != "Available" for port in ports):
              available_location.append("BACK")
              will_send_email = True
              break
        if will_send_email:
          send_email()
          break
      else:
        if front_num_available > 0:
          available_location.append("FRONT")
        if back_num_available > 0:
          available_location.append("BACK")
        if available_location:
          send_email()
          break

    except KeyboardInterrupt:
      logger.error("Interrupted! Exiting...")
      break

  driver.close()
  logger.superinfo("Have a wonderful day!")
