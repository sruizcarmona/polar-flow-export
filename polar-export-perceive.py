from selenium import webdriver
import requests
import re
import time
import sys
import os
from datetime import datetime
import csv
import pandas

FLOW_URL = "https://flow.polar.com"

def login(driver, username, password):
    # driver = webdriver.Chrome() # for testing purposes
    driver.get("%s/login" % FLOW_URL)
    # sleep for 1 second to make sure the page is loaded
    time.sleep(1)
    # driver.find_element("id", "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll").click()
    driver.find_element("id", "CybotCookiebotDialogBodyButtonDecline").click() # new step after polar update 7/10/24 -  decline cookies
    driver.find_element("id", "login").click() # new step after polar update 7/10/24
    # sleep for 5 second to make sure the page is loaded
    time.sleep(5)
    driver.find_element("name", "username").send_keys(username)
    driver.find_element("name", "password").send_keys(password)
    # updated the line below because it was not working after polar update 7/10/24
    # driver.find_element("id", "login").click()
    driver.find_element("xpath","//button[@class='btn btn-md btn-primary btn-block']").click() # new step after polar update 7/10/24

def get_exercise_ids(driver, year, month):
    driver.get("%s/diary/%s/month/%s" % (FLOW_URL, year, month))
    time.sleep(2)
    ids = map(
        # The subscript removes the prefix
        lambda e: e.get_attribute("href")[len("https://flow.polar.com/training/analysis2/"):],
        driver.find_elements("xpath","//div[@class='event event-month exercise']/a") +
        driver.find_elements("xpath","//div[@class='event event-month exercise event-item--has-target']/a")
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
    rcsv = s.get("%s/api/export/training/csv/%s" % (FLOW_URL, exercise_id))
    if r.status_code == 200:
        # get the tcx data
        tcx_data = r.text
        # get the csv data
        csv_data = rcsv.text
        # get sport from csv_data
        # csv_data is a raw csv file, split by lines, take the second line (first are headers)
        # then split by comma and take the second value (SPORT)
        try:
            mysport = csv_data.splitlines()[1].split(',')[1]
        except IndexError:
            mysport = 'UNKNOWN'

        try:
            # get the filename from the response headers for tcx and csv
            filename = _get_filename(r)
            # filenamecsv = _get_filename(rcsv)
            # make directory the first time an activity is found
            if not os.path.exists(output_dir):
                #create a new directory because it does not exist
                os.makedirs(output_dir)
                print("Created directory %s" % output_dir)
            # write tcx file
            outfile_path_tmp = os.path.join(output_dir, filename)
            # add string to tcx file to include sport
            outfile_path = outfile_path_tmp.replace('.TCX', '_SPORT_%s.TCX' % mysport)
            with open(outfile_path, 'w') as outfile:
                outfile.write(tcx_data)
            print("Wrote file %s" % outfile_path)
            # fix tcx file name to include sport
            # not needed in the end
            # _add_sport_to_tcx(outfile_path, outfilecsv_path)
        except KeyError as e:
            print(e)
    else:
        print("Failed to download file. Status code: %s" % r.status_code)

def list_months(startdate, enddate):
    # get month and year from startdate and enddate
    startmonth = startdate.month
    startyear = startdate.year
    endmonth = enddate.month
    endyear = enddate.year
    # get list of months from startdate to enddate
    year_month = []
    for year in range(startyear, endyear + 1):
        if year == startyear:
            start_month = startmonth
        else:
            start_month = 1
        if year == endyear:
            end_month = endmonth
        else:
            end_month = 12
        for month in range(start_month, end_month + 1):
            year_month.append((year, month))
    return year_month

def run(driver, username, password, output_dir, startdate, enddate):
    login(driver, username, password)

    time.sleep(5)
    # loop through months in the date range
    year_month = list_months(startdate, enddate)
    for year, month in year_month:
        exercise_ids = get_exercise_ids(driver, year, month)
        for ex_id in exercise_ids:
            export_exercise(driver, ex_id, output_dir)

if __name__ == "__main__":
    try:
        (pwdfile, outdir, startdate, enddate) = sys.argv[1:]
        # (pwdfile, outdir, startdate, enddate) = ('test.csv', 'test', '1/24', '2/24')
    except ValueError:
        sys.stderr.write(("Usage: python %s <csvfile> <outdir> <startdate MM/YY> <enddate MM/YY> \n") % sys.argv[0])
        sys.exit(1)
    # convert startdate and enddate to datetime objects
    try:
        startdate = datetime.strptime(startdate, '%m/%y')  
        enddate = datetime.strptime(enddate, '%m/%y')
        # check if enddate is in the future, if it is, set it to today
        if enddate > datetime.now():
            enddate = datetime.now()
            print("End date is in the future, setting it to today: %s" % enddate.strftime('%-m/%y'))
    except ValueError:
        sys.stderr.write("Please provide correct dates in the format MM/YY\n")
        sys.exit(1)
    # check if startdate is before enddate
    if startdate > enddate:
        sys.stderr.write("Start date is after End date, please provide correct dates\n")
        sys.exit(1)
    # get usernames and passwords from a csv file
    with open(pwdfile) as f:
        # read csv and remove newline characters
        # lines = f.read().splitlines()
        reader = csv.reader(f)
        lines = [[c.replace('\ufeff', '') for c in row] for row in reader]
        for line in lines:
            # username, password, userid = line.split(',')
            username, password, userid = line
            output_dir = outdir + '/' + userid
            # check if output_dir exists, if it does, skip user, else create the directory
            if os.path.exists(output_dir):
                # check if directory is empty, if it is, process participant, else skip
                if not os.listdir(output_dir):
                    print("Directory %s is empty, processing participant %s (%s to %s)" % (output_dir, userid, startdate.strftime('%b %Y'), enddate.strftime('%b %Y')))
                else:
                    print("Directory %s already exists and contains activities, skipping participant %s" % (output_dir, userid))
                    continue
            else:
                #create a new directory because it does not exist
                os.makedirs(output_dir)
                print("New participant: %s (downloading from %s to %s)" % (userid, startdate.strftime('%b %Y'), enddate.strftime('%b %Y')))

            # run chrome        
            driver = webdriver.Chrome()
            try:
                run(driver, username, password, output_dir, startdate, enddate)
            finally:
                # print user finished
                print("Finished user %s" % userid)
                driver.quit()
