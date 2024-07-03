from selenium import webdriver
import requests
import re
import time
import sys
import os

FLOW_URL = "https://flow.polar.com"

def login(driver, username, password):
    driver.get("%s/login" % FLOW_URL)
    # sleep for 1 second to make sure the page is loaded
    time.sleep(1)
    driver.find_element("name", "email").send_keys(username)
    driver.find_element("name", "password").send_keys(password)
    driver.find_element("id", "login").click()

def get_exercise_ids(driver, year, month):
    driver.get("%s/diary/%s/month/%s" % (FLOW_URL, year, month))
    time.sleep(2)
    ids = map(
        # The subscript removes the prefix
        lambda e: e.get_attribute("href")[len("https://flow.polar.com/training/analysis/"):],
        driver.find_elements("xpath","//div[@class='event event-month exercise']/a")
    )
    return ids

def export_exercise(driver, exercise_id, output_dir):
    def _load_cookies(session, cookies):
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

    s = requests.Session()
    _load_cookies(s, driver.get_cookies())

    # new function to raise an error if the filename cannot be extracted (usually with multisport activities)
    def _get_filename(r):
        content_disposition = r.headers.get('Content-Disposition')
        if content_disposition:
            regex = r"filename=\"([\w._-]+)\""
            match = re.search(regex, content_disposition)
            if match:
                return match.group(1)
            else:
                raise ValueError("Filename could not be extracted from Content-Disposition header.")
        else:
            # Provide a default filename or raise an error
            raise KeyError("Response does not contain a 'Content-Disposition' header.")

    r = s.get("%s/api/export/training/tcx/%s" % (FLOW_URL, exercise_id))
    if r.status_code == 200:
        tcx_data = r.text
        try:
            filename = _get_filename(r)
            # check whether the specified path exists or not
            out_exists = os.path.exists(output_dir)
            if not out_exists:
                #create a new directory because it does not exist
                os.makedirs(output_dir)
                print("Created directory %s" % output_dir)
            outfile_path = os.path.join(output_dir, filename)
            with open(outfile_path, 'w') as outfile:
                outfile.write(tcx_data)
            print("Wrote file %s" % filename)
        except KeyError as e:
            print(e)
    else:
        print("Failed to download file. Status code: %s" % r.status_code)
    

def run(driver, username, password, year, output_dir):
    login(driver, username, password)

    time.sleep(5)
    # loop through all months in year
    for month in range(1, 13):
        exercise_ids = get_exercise_ids(driver, year, month)
        for ex_id in exercise_ids:
            export_exercise(driver, ex_id, output_dir)

if __name__ == "__main__":
    try:
        (pwdfile, year) = sys.argv[1:]
    except ValueError:
        sys.stderr.write(("Usage: %s <year>\n") % sys.argv[0])
        sys.exit(1)

    # get usernames and passwords from a csv file
    with open(pwdfile) as f:   
        # read csv and remove newline characters
        lines = f.read().splitlines()
    for line in lines:
        username, password, userid = line.split(',')
        driver = webdriver.Chrome()
        try:
            run(driver, username, password, year, userid)
        finally:
            driver.quit()