from datetime import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def to_datetime(s):
    return datetime.strptime(s, '%I:%M %p')

def main(assignment_list, cal_id):
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)
    
    #create new calendar if none exists
    if cal_id == "":
        print("New calendar ID has been saved in achieve_login.json.")
        calendar = {
          'summary' : 'Achieve Homework',
          'timeZone' : 'America/Los_Angeles'
        }
        
        loginfo = {}
        created_cal = service.calendars().insert(body=calendar).execute()
        cal_id = created_cal['id']
        with open("achieve_login.json", 'r') as log:
          access_log = json.load(log)
          loginfo = {
            "username" : access_log['username'],
            "password" : access_log['password'],
            "class_token" : access_log['class_token'],
            "calendar_id" : cal_id
          }
        with open("achieve_login.json", 'w') as log:
          json.dump(loginfo, log)
          
    #add each assignment to the calendar
    for assignment in assignment_list:
      event = {
        'summary' : assignment[0],
        'start' : {
            'dateTime' : assignment[1],
            'timeZone' : 'America/Los_Angeles'
        },
        'end' : {
            'dateTime' : assignment[1],
            'timeZone' : 'America/Los_Angeles'
        }
      }
      service.events().insert(calendarId=cal_id, body=event).execute()

  except HttpError as error:
    print(f"An error occurred: {error}")
    if error.reason == "Not Found":
      print("Calendar not found. Create a new calendar and continue?")
      response = input("Input Y to continue, otherwise enter any character: ")
      if (response == "Y"):
        main(assignment_list, "")

#convert string from achieve -> formatted datetime -> str
def mdy_to_ymd(d: str) -> datetime:
    return datetime.strptime(d, '%b %d, %Y %I:%M %p').strftime('%Y-%m-%dT%H:%M:%S')

#searches for an element with a given attribute
def search_att_in_elems(loc: By, fdr: str, att: str, att_eq: str) -> WebElement:
    elems = dr.find_elements(loc, fdr)
    if len(elems) == 0:
        raise Exception("No elements found. Check that '" + fdr + "' is spelled correctly.")
    for elem in elems:
        if elem.get_attribute(att) == att_eq:
            return elem
    raise Exception("Either no elements with attribute '" + att + "' has been found or no attribute has value:'" + att_eq + "'. Check for spelling errors or that it exists.")

if __name__ == "__main__":
    #get all achieve assignments
    options = webdriver.ChromeOptions()
    dr = webdriver.Chrome(options=options)
    dr.get('https://iam.macmillanlearning.com/login?retURL=https://achieve.macmillanlearning.com/courses')
    dr.implicitly_wait(10)
    with open("achieve_login.json", "r") as a_log_info:
        a_log = json.load(a_log_info)
    
    print('Accessing achieve...')
    
    #enter login information and log in 
    dr.find_element(By.ID, 'username').send_keys(a_log["username"])
    dr.find_element(By.ID, 'password').send_keys(a_log["password"])
    dr.find_element(By.ID, 'signin').click()
    dr.find_element(By.CSS_SELECTOR, '[id="usercentrics-root"]').shadow_root.find_element(By.CSS_SELECTOR, '[data-testid="uc-accept-all-button"]').click()
    search_att_in_elems(By.TAG_NAME, 'a', 'href', 'https://achieve.macmillanlearning.com/courses/' + a_log["class_token"]).click()
    
    #2d array formatted as [["assignment name1", ]]
    assignment_list = []
    
    #grab "This week" container and search for each assignment <div> that contains a weekday in the first few characters of the text component
    this_week = dr.find_element(By.ID, "panel-content-this-week").find_element(By.TAG_NAME, 'ul').find_elements(By.CSS_SELECTOR, '[role="button"]')
    for elem in this_week:
        info_list = []
        info_list.append(elem.get_attribute("data-test-id"))
        spans = elem.find_elements(By.TAG_NAME, 'span')
        for span in spans:
            if span.text[0:3] == "Mon" or span.text[0:3] == "Tues" or span.text[0:3] == "Wed" or span.text[0:3] == "Thu" or span.text[0:3] == "Fri" or span.text[0:3] == "Sat" or span.text[0:3] == "Sun":
                #format and add to list
                sptext = span.text
                sptext = mdy_to_ymd(sptext[5:12] + ' 2024 ' + sptext[13:])
                info_list.append(sptext)
        assignment_list.append(info_list)

    print("Achieve assignments accessed; adding to calendar")
    #send to google calendar
    main(assignment_list, a_log["calendar_id"])