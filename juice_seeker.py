import os
import time
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import requests
import numpy as np
import scipy.interpolate as si

# Curve base:
points = [[0, 0], [0, 2], [2, 3], [4, 0], [6, 3], [8, 2], [8, 0]];
points = np.array(points)

x = points[:,0]
y = points[:,1]


t = range(len(points))
ipl_t = np.linspace(0.0, len(points) - 1, 100)

x_tup = si.splrep(t, x, k=3)
y_tup = si.splrep(t, y, k=3)

x_list = list(x_tup)
xl = x.tolist()
x_list[1] = xl + [0.0, 0.0, 0.0, 0.0]

y_list = list(y_tup)
yl = y.tolist()
y_list[1] = yl + [0.0, 0.0, 0.0, 0.0]

x_i = si.splev(ipl_t, x_list) # x interpolate values
y_i = si.splev(ipl_t, y_list) # y interpolate values


REFRESH_TIME = 0.5 # sec

print("Getting browser...")
# options = webdriver.ChromeOptions() #options. ...
driver = webdriver.Chrome()

print("Opening website...")
# Opening the website
driver.get("https://sky.shellrecharge.com/evowner/portal/locate-charger")

# finding the button using ID
button = driver.find_element(value="driver-login")

# clicking on the button
button.click()

while not driver.find_elements(value="mat-input-2"):
  continue

email_txtbx = driver.find_element(value="mat-input-1")
email_txtbx.send_keys("***********@gmail.com") #
pw_txtbx = driver.find_element(value="mat-input-2")
pw_txtbx.send_keys("***************") #
time.sleep(5)
# TODO: not working yet
# for mouse_x, mouse_y in zip(x_i, y_i):
#     ActionChains(driver).move_by_offset(mouse_x, mouse_y)
#     ActionChains(driver).perform()

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
time.sleep(2)

# ============================================================================
# audioBtnFound = False
# audioBtnIndex = -1
# filename = '1.mp3'
# allIframesLen = driver.find_elements(by=By.TAG_NAME, value='iframe')
# delayTime = 2
# audioToTextDelay = 10
# googleIBMLink = 'https://speech-to-text-demo-nlu.mybluemix.net/'

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
#     root = driver.find_elements(by=By.ID, value='root').find_elements(by=By.CLASS_NAME, value='dropzone _container _container_large')
#     btn = driver.find_element(By.XPATH, '//*[@id="root"]/div/input')
#     btn.send_keys('1.mp3')
#     # Audio to text is processing
#     time.sleep(delayTime)
#     #btn.send_keys(path)
#     print("4")
#     # Audio to text is processing
#     time.sleep(audioToTextDelay)
#     print("5")
#     text = driver.find_element(By.XPATH, '//*[@id="root"]/div/div[7]/div/div/div').find_elements(by=By.TAG_NAME, value='span')
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


# try:
#     audioBtn = driver.find_elements(by=By.ID, value='recaptcha-audio-button') or driver.find_elements(by=By.ID, value='recaptcha-anchor')
#     audioBtn.click()
#     audioBtnFound = True
#     break
# except Exception as e:
#     pass
      
# if audioBtnFound:
#     try:
#         while True:
#             href = driver.find_elements(by=By.ID, value='audio-source').get_attribute('src')
#             response = requests.get(href, stream=True)
#             saveFile(response,filename)
#             response = audioToText(os.getcwd() + '/' + filename)
#             driver.switch_to.default_content()
#             iframe = driver.find_elements(by=By.TAG_NAME, value='iframe')[audioBtnIndex] # it is not an iframe anymore....
#             driver.switch_to.frame(iframe)
#             inputbtn = driver.find_elements(by=By.ID, value='audio-response')
#             inputbtn.send_keys(response)
#             inputbtn.send_keys(Keys.ENTER)
#             time.sleep(2)
#             errorMsg = driver.find_elements(by=By.CLASS_NAME, value='rc-audiochallenge-error-message')[0]
#             if errorMsg.text == "" or errorMsg.value_of_css_property('display') == 'none':
#                 print("Success")
#                 break
#     except Exception as e:
#             print(e)
#             print('Caught. Need to change proxy now')
#     else:
#         print('Button not found. This should not happen.')

# ============================================================================
time.sleep(10)

# finding the button using ID
login = driver.find_element(by=By.CLASS_NAME, value="green_btn_lg.customize-primary-bg.mat-button")

# clicking on the button
login.click()
print("Logging in...")
while driver.find_elements(value="mat-input-2"):
  continue

def get_availabilities(driver):
  output_dict = dict()
  html = BeautifulSoup(driver.page_source, features="lxml")
  for card in html.body.find_all('mat-card', attrs={"class": "notify_list"}):
    station_id = int(card.find('div', attrs={"class": "charger-detail-head"}).span.text.split(':')[-1])
    output_dict.setdefault(station_id, dict())
    chargers = card.find('div', attrs={"class": "charger-detail-body"}).find_all('div', attrs={"class": "charger_info"})
    for charger in chargers:
      charger_num = int(charger.find('div', attrs={"class": "number_charge"}).span.text)
      charger_avail = charger.find('div', attrs={"class": "available_info"}).span.text.lstrip('(').rstrip(')')
      output_dict[station_id][charger_num] = charger_avail
  return output_dict

driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
while not any([el.text == "521407_4100 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
  continue
back_spots = [el for el in driver.find_elements(by=By.TAG_NAME, value="a") if el.text == "521407_4100 Bayside"][0]
back_spots.click()
while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
  continue

back_availabilities = get_availabilities(driver)
  
driver.get('https://sky.shellrecharge.com/evowner/portal/manage-account/favorites')
while not any([el.text == "521412_4000 Bayside" for el in driver.find_elements(by=By.TAG_NAME, value="a")]):
  continue
back_spots = [el for el in driver.find_elements(by=By.TAG_NAME, value="a") if el.text == "521412_4000 Bayside"][0]
back_spots.click()
while not driver.find_elements(by=By.CLASS_NAME, value="charger-detail-head"):
  continue

front_availabilities = get_availabilities(driver)

print(back_availabilities)
print(front_availabilities)

driver.close()
