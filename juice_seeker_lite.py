import requests
import logging
import os
import json
from mailjet_rest import Client
from dotenv import load_dotenv
load_dotenv()

DEBUG_MODE = False
CHANGE_MODE = True
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
  for location, location_id in LOCATION_TO_ID.items():
    location_availabilities = availabilities.setdefault(location, dict())
    response = requests.get(URL_TEMPLATE.format(location_id=location_id))
    if response.status_code != 200:
        raise ConnectionError(f"Status code not success.")

    response_data = response.json()

    if response_data["status"] != "SUCCESS":
        raise RuntimeError(f"Failed to get charger status for {location}: {response_data['message']}")
    
    for station in response_data["data"]["evses"]:
        location_availabilities.setdefault(station["evseId"], dict())
        for port in station["ports"]:
            location_availabilities[station["evseId"]][port['portName']] = port["portStatus"]
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
  email_segments.append(f"T1:")
  email_segments.extend([f"{k}\t{v}" for k, v in availabilities["T1"].items()])
  email_segments.append(f"\nT2:")
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

if __name__ == '__main__':
  prev_availabilities = None
  while True:
    try:
      logger.superinfo("Seeking juice...")
      availabilities = get_juice()
      availabilities = handle_excludes(availabilities)

      logger.info(json.dumps(availabilities, indent=2))

      if prev_availabilities is None:
        prev_availabilities = availabilities
      
      available_location = []
      
      if CHANGE_MODE:
        will_send_email = False
        if prev_availabilities != availabilities:
          for location, location_avail in availabilities.items():
            for station, ports in location_avail.items():
              if any(((ports[port] == "AVAILABLE" and prev_availabilities[location][station][port] != "AVAILABLE") for port in ports)):
                available_location.append(location)
                will_send_email = True
                break
        
        if will_send_email:
          logger.info("Sending email...")
          send_email()
          break
      
      else:
        for location, location_avail in availabilities.items():
          if location_avail["num_available"] > 0:
            available_location.append(location)
        if available_location:
          send_email()
          break

    except KeyboardInterrupt:
      logger.error("Interrupted! Exiting...")
      break

    except Exception as e:
      print(e)
      continue

  logger.superinfo("Have a wonderful day!")
