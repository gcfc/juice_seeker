import requests
import logging
import os
import json
import time
from mailjet_rest import Client
from dotenv import load_dotenv
load_dotenv()

EXIT_WHEN_FOUND = False
DEBUG_MODE = False
# These stations and ports don't work
EXCLUDED_STATIONS_AND_PORTS = [(52957, 1), (52958, 1)]

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


URL_TEMPLATE = "https://sky.shellrecharge.com/greenlots/coreapi/v4/sites/search/{location_id}"
LOCATION_TO_ID = {"T1": 1944, "T2": 1902}

def get_juice():
  availabilities = dict()
  received_locations = []
  for location, location_id in LOCATION_TO_ID.items():
    location_availabilities = availabilities.setdefault(location, dict())
    response = requests.get(URL_TEMPLATE.format(location_id=location_id))
    if response.status_code != 200:
        raise ConnectionError("Status code not success.")

    response_data = response.json()

    if response_data["status"] != "SUCCESS":
        logger.info(f"Failed to get charger status for {location}: {response_data['message']}")
        continue
    
    for station in response_data["data"]["evses"]:
        location_availabilities.setdefault(station["evseId"], dict())
        for port in station["ports"]:
            location_availabilities[station["evseId"]][port['portName']] = port["portStatus"]
    received_locations.append(location)
  if not received_locations:
    info_print = "Seeking juice..."
  else:
    info_print = "Seeking juice from " + " and ".join(received_locations) + "..."
  logger.superinfo(info_print)
  return availabilities

def handle_excludes(availabilities):
  # Yeet the ones that are reserved / don't work
  for exclude_station, exclude_port in EXCLUDED_STATIONS_AND_PORTS:
    for location, location_avail in availabilities.items():
      station_result = location_avail.get(str(exclude_station), None)
      if station_result is not None:
        station_result.pop(str(exclude_port), None)
      stations_to_delete = [station for station, port in location_avail.items() if port == dict()]
      for station in stations_to_delete:
        location_avail.pop(station)
  return availabilities

def send_email():
  api_key = os.environ['API_KEY']
  api_secret = os.environ['API_SECRET']
  email_segments = []
  email_segments.append(f"Charger found in {' AND '.join(available_location)}!")
  email_segments.append("T1:")
  email_segments.extend([f"{k}\t{v}" for k, v in availabilities["T1"].items()])
  email_segments.append("\nT2:")
  email_segments.extend([f"{k}\t{v}" for k, v in availabilities["T2"].items()])
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

def send_mac_notification():
  title = f"{' and '.join(available_location)} Charger Found! {time.strftime("%H:%M:%S")}"
  text = "GO GO GO!"
  
  os.system('afplay /Users/gechen/Downloads/knock_brush.mp3')
  os.system('afplay /Users/gechen/Downloads/knock_brush.mp3')
  os.system("""
            osascript -e 'display notification "{}" with title "{}"'
            """.format(text, title))

if __name__ == '__main__':
  prev_availabilities = {loc : dict() for loc in LOCATION_TO_ID}
  while True:
    try:
      availabilities = get_juice()
      availabilities = handle_excludes(availabilities)

      logger.info(json.dumps(availabilities, indent=2))

      # Initialize prev_availabilities if haven't
      for location, location_avail in availabilities.items():
        if prev_availabilities[location] == dict() and availabilities[location] != dict():
          prev_availabilities[location] = availabilities[location]
          logger.superinfo(json.dumps(prev_availabilities[location], indent=2))
      
      available_location = []
      
      will_send_email = False
      for location, location_avail in availabilities.items():
        if prev_availabilities[location] != availabilities[location] and availabilities[location] != dict():
          for station, ports in location_avail.items():
            if any(((ports[port] == "AVAILABLE" and prev_availabilities[location][station][port] == "BUSY") for port in ports)):
              available_location.append(location)
              will_send_email = True
              break
      
      if will_send_email:
        logger.info("Sending email...")
        send_email()
        send_mac_notification()
        if EXIT_WHEN_FOUND:
          break
      
      # Save info
      for location, location_avail in availabilities.items():
        if prev_availabilities[location] != dict() and availabilities[location] != dict():
          prev_availabilities[location] = availabilities[location]
        logger.info(json.dumps(prev_availabilities[location], indent=2))
    
    except KeyboardInterrupt:
      logger.error("Interrupted! Exiting...")
      break

    except Exception as e:
      logger.error(e)
      continue

  logger.superinfo("Have a wonderful day!")
  quit()
