from dotenv import load_dotenv
from mailjet_rest import Client
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver import ActionChains
from selenium import webdriver
import os
import json
import numpy as np
import scipy.interpolate as si
import pprint
pp = pprint.PrettyPrinter(indent=2)

load_dotenv()


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
  audio_button_found = False
  driver.switch_to.frame(captcha_iframe)
  while not captcha_ok:
    holder = driver.find_element(by=By.CLASS_NAME, value='rc-anchor-checkbox-holder')
    span = holder.find_element(by=By.TAG_NAME, value='span')
    # audio_button = driver.find_elements(by=By.CLASS_NAME, value='rc-button-audio')
    # audio_button2 = driver.find_elements(by=By.ID, value="recaptcha-audio-button")
    # print(audio_button, audio_button2)
    # audio_button_found = bool(len(audio_button))
    if "recaptcha-checkbox-checked" in span.get_attribute("class"):
      captcha_ok = True
      print("Got u good lmao")
    elif audio_button_found:
      print("Audio button found")
      # TODO

  # finding the login button
  driver.switch_to.default_content()
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
  print("Getting stations...")
  driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
  while not any([el.text == "521407_4100 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
    continue
  back_spots = [el for el in driver.find_elements(
      by=By.TAG_NAME, value="a") if el.text == "521407_4100 Bayside"][0]
  back_spots.click()
  while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
    continue

  back_availabilities = read_station(driver)
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
      front_availabilities.pop(52447)
      back_total = sum(len(v) for v in back_availabilities.values())
      back_num_available = sum(vv == 'Available' for v in back_availabilities.values()
                               for vv in v.values())
      front_total = sum(len(v) for v in front_availabilities.values())
      front_num_available = sum(vv == 'Available' for v in front_availabilities.values()
                                for vv in v.values())

      if (back_num_available > 0) or (front_num_available > 0):
        send_email()
        break

    except KeyboardInterrupt:
      print("Interrupted! Exiting...")
      break

  driver.close()
  print("Have a wonderful day!")


# ============================================================================
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from http_request_randomizer.requests.proxy.requestProxy
# import RequestProxy
# import os, sys
# import time,requests
# from bs4 import BeautifulSoup
# delayTime = 2
# audioToTextDelay = 10
# filename = '1.mp3'
# byPassUrl = 'https://www.google.com/recaptcha/api2/demo'
# googleIBMLink = 'https://speech-to-text-demo.ng.bluemix.net/'
# option = webdriver.ChromeOptions()
# option.add_argument('--disable-notifications')
# option.add_argument("--mute-audio")
# # option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
# option.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile/14E5239e Safari/602.1")
# def audioToText(mp3Path):
#     print("1")
#     driver.execute_script('''window.open("","_blank");''')
#     driver.switch_to.window(driver.window_handles[1])
#     print("2")
#     driver.get(googleIBMLink)
#     delayTime = 10
#     # Upload file
#     time.sleep(1)
#     print("3")
#     # Upload file
#     time.sleep(1)
#     root = driver.find_element_by_id('root').find_elements_by_class_name('dropzone _container _container_large')
#     btn = driver.find_element(By.XPATH, '//*[@id="root"]/div/input')
#     btn.send_keys('C:/Users/AbdulBasit/Documents/google-captcha-bypass/1.mp3')
#     # Audio to text is processing
#     time.sleep(delayTime)
#     #btn.send_keys(path)
#     print("4")
#     # Audio to text is processing
#     time.sleep(audioToTextDelay)
#     print("5")
#     text = driver.find_element(By.XPATH, '//*[@id="root"]/div/div[7]/div/div/div').find_elements_by_tag_name('span')
#     print("5.1")
#     result = " ".join( [ each.text for each in text ] )
#     print("6")
#     driver.close()
#     driver.switch_to.window(driver.window_handles[0])
#     print("7")
#     return result
# def saveFile(content,filename):
#     with open(filename, "wb") as handle:
#         for data in content.iter_content():
#             handle.write(data)
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=option)
# driver.get(byPassUrl)
# time.sleep(1)
# googleClass = driver.find_elements_by_class_name('g-recaptcha')[0]
# time.sleep(2)
# outeriframe = googleClass.find_element_by_tag_name('iframe')
# time.sleep(1)
# outeriframe.click()
# time.sleep(2)
# allIframesLen = driver.find_elements_by_tag_name('iframe')
# time.sleep(1)
# audioBtnFound = False
# audioBtnIndex = -1
# for index in range(len(allIframesLen)):
#     driver.switch_to.default_content()
#     iframe = driver.find_elements_by_tag_name('iframe')[index]
#     driver.switch_to.frame(iframe)
#     driver.implicitly_wait(delayTime)
#     try:
#         audioBtn = driver.find_element_by_id('recaptcha-audio-button') or driver.find_element_by_id('recaptcha-anchor')
#         audioBtn.click()
#         audioBtnFound = True
#         audioBtnIndex = index
#         break
#     except Exception as e:
#         pass
# if audioBtnFound:
#     try:
#         while True:
#             href = driver.find_element_by_id('audio-source').get_attribute('src')
#             response = requests.get(href, stream=True)
#             saveFile(response,filename)
#             response = audioToText(os.getcwd() + '/' + filename)
#             print(response)
#             driver.switch_to.default_content()
#             iframe = driver.find_elements_by_tag_name('iframe')[audioBtnIndex]
#             driver.switch_to.frame(iframe)
#             inputbtn = driver.find_element_by_id('audio-response')
#             inputbtn.send_keys(response)
#             inputbtn.send_keys(Keys.ENTER)
#             time.sleep(2)
#             errorMsg = driver.find_elements_by_class_name('rc-audiochallenge-error-message')[0]
#             if errorMsg.text == "" or errorMsg.value_of_css_property('display') == 'none':
#                 print("Success")
#                 break
#     except Exception as e:
#         print(e)
#         print('Caught. Need to change proxy now')
# else:
#     print('Button not found. This should not happen.')

# ============================================================================
