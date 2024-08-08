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
    driver.get("%s/login" % FLOW_URL)
    # sleep for 1 second to make sure the page is loaded
    time.sleep(5)
    driver.find_element("name", "email").send_keys(username)
    driver.find_element("name", "password").send_keys(password)
    driver.find_element("id", "login").click()

def get_exercise_ids(driver, year, month):
    driver.get("%s/diary/%s/month/%s" % (FLOW_URL, year, month))
    time.sleep(2)
    ids = map(
        # The subscript removes the prefix
        lambda e: e.get_attribute("href")[len("https://flow.polar.com/training/analysis/"):],
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
    
    # # function to add sport to tcx file after reading csv
    # # not needed in the end, csv can be read on the fly
    # def _add_sport_to_tcx(tcx_file, csv_file):
    #     # read csv file, only the headers and the first row
    #     df = pandas.read_csv(csv_file, nrows=1)
    #     # get value for column 'Sport'
    #     sport = df['Sport'][0]
    #     # change name of tcx to include sport
    #     new_tcx = tcx_file.replace('.TCX', '_SPORT_%s.TCX' % sport)
    #     # change file name of tcx file
    #     os.rename(tcx_file, new_tcx)
    #     # remove csv file
    #     os.remove(csv_file)

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
        mysport = csv_data.splitlines()[1].split(',')[1]

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


def run(driver, username, password, output_dir):
    login(driver, username, password)

    time.sleep(5)
    # loop through years from 2022 to today
    current_year = datetime.now().year
    for year in range(2023, current_year + 1):
        # loop through all months in year
        for month in range(1, 13):
            exercise_ids = get_exercise_ids(driver, year, month)
            for ex_id in exercise_ids:
                export_exercise(driver, ex_id, output_dir)

if __name__ == "__main__":
    try:
        (pwdfile, outdir) = sys.argv[1:]
    except ValueError:
        sys.stderr.write(("Usage: %s <csvfile> <outdir>\n") % sys.argv[0])
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
            print("Directory %s already exists, skipping participant %s" % (output_dir, userid))
            continue
        else:
            #create a new directory because it does not exist
            os.makedirs(output_dir)
            print("New participant: %s" % userid)

        # run chrome        
        driver = webdriver.Chrome()
        try:
            run(driver, username, password, output_dir)
        finally:
            # print user finished
            print("Finished user %s" % userid)
            driver.quit()
