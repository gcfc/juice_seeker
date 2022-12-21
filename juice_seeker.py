from dotenv import load_dotenv
from mailjet_rest import Client
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver import ActionChains
from selenium import webdriver
from utils import *
import os
import json
import pprint
pp = pprint.PrettyPrinter(indent=2)

load_dotenv()

DEBUG_MODE = True


def setup():
  print("Getting browser...")
  options = webdriver.ChromeOptions()
  # TODO: make it headless (and other options)
  driver = webdriver.Chrome(options=options)

  print("Opening website...")
  # Opening the website
  driver.get("https://sky.shellrecharge.com/evowner/account/sign-in")

  while not driver.find_elements(value="mat-input-1"):
    continue

  print("Entering info...")
  email_txtbx = driver.find_element(value="mat-input-0")
  email_txtbx.send_keys(os.environ['GREENSHELL_USERNAME'])
  pw_txtbx = driver.find_element(value="mat-input-1")
  pw_txtbx.send_keys(os.environ['GREENSHELL_PASSWORD'])
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

  # click im not robot
  captcha_box = WebDriverWait(driver, 2).until(
      ec.presence_of_element_located(
          (
              By.ID, 'g-recaptcha-response'
          )
      )
  )

  driver.execute_script("arguments[0].click()", captcha_box)
  print('I am not a robot I swear!')

  # Error Handing for captcha
  captcha_ok = False
  audio_sent = False

  while not captcha_ok:
    driver.switch_to.frame(captcha_iframe)
    holder = driver.find_element(by=By.CLASS_NAME, value='rc-anchor-checkbox-holder')
    span = holder.find_element(by=By.TAG_NAME, value='span')

    if "recaptcha-checkbox-checked" in span.get_attribute("class"):
      captcha_ok = True
      print("Got u good lmao")
    elif not audio_sent:
      driver.switch_to.default_content()
      iframe = driver.find_element(
          by=By.XPATH, value="//iframe[@title='recaptcha challenge expires in two minutes']")
      driver.switch_to.frame(iframe)
      audio_button_list = driver.find_elements(by=By.ID, value='recaptcha-audio-button')
      if audio_button_list:
        print("Audio button found")
        audio_button = audio_button_list[0]
        audio_button.click()
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

  # finding the login button
  login = driver.find_element(
      by=By.CLASS_NAME, value="green_btn_lg.customize-primary-bg.mat-button")

  # clicking on the button
  login.click()

  print("Logging in...")
  while driver.find_elements(value="mat-input-1"):
    continue
  print("Logged in!")

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
      output_dict[station_id][charger_num] = charger_avail
  return output_dict


def get_front_and_back(driver):
  print("Checking stations...")
  driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
  while not any([el.text == "521407_4100 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
    continue
  back_spots = [el for el in driver.find_elements(
      by=By.TAG_NAME, value="a") if el.text == "521407_4100 Bayside"][0]
  back_spots.click()
  while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
    continue

  back_availabilities = read_station(driver)
  if DEBUG_MODE:
    print(f"Looked at the back")
    pp.pprint(back_availabilities)

  driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
  while not any([el.text == "521412_4000 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
    continue
  back_spots = [el for el in driver.find_elements(
      by=By.TAG_NAME, value="a") if el.text == "521412_4000 Bayside"][0]
  back_spots.click()
  while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
    continue

  front_availabilities = read_station(driver)
  if DEBUG_MODE:
    print(f"Looked at the front")
    pp.pprint(front_availabilities)

  return front_availabilities, back_availabilities


def send_email():
  api_key = os.environ['API_KEY']
  api_secret = os.environ['API_SECRET']
  email_segments = []
  email_segments.append(f"Front: {front_num_available}/{front_total}")
  email_segments.extend([f"{k}\t{v}" for k, v in front_availabilities.items()])
  email_segments.append(f"\nBack: {back_num_available}/{back_total}")
  email_segments.extend([f"{k}\t{v}" for k, v in back_availabilities.items()])
  email_text = "\n".join(email_segments)
  print(email_text)

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
  result = mailjet.send.create(data=data)
  if result.status_code == 200:
    print("Email sent successfully!")

  print("Sent API Response:", json.dumps(result.json(), indent=2))


if __name__ == '__main__':
  driver = setup()
  while True:
    try:
      front_availabilities, back_availabilities = get_front_and_back(driver)
      front_availabilities.pop(52447)  # This station doesn't work
      back_total = sum(len(v) for v in back_availabilities.values())
      back_num_available = sum(vv == 'Available' for v in back_availabilities.values()
                               for vv in v.values())
      front_total = sum(len(v) for v in front_availabilities.values())
      front_num_available = sum(vv == 'Available' for v in front_availabilities.values()
                                for vv in v.values())

      if ((back_num_available > 0) or (front_num_available > 0)) and not DEBUG_MODE:
        send_email()
        break

    except KeyboardInterrupt:
      print("Interrupted! Exiting...")
      break

  driver.close()
  print("Have a wonderful day!")
