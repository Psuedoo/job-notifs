import http.client, urllib, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from tinydb import TinyDB
from deepdiff import DeepDiff
from dotenv import load_dotenv

load_dotenv()


def get_job_postings():
    URL = "https://www.creditkarma.com/careers/jobs/search?ck-department=engineering"

    options = webdriver.ChromeOptions()
    args = ["--headless", "--disable-gpu", "--window-size=1920,1080"]
    for arg in args:
        options.add_argument(arg)
    options.add_argument
    driver = webdriver.Chrome(options=options)
    driver.get(URL)
    elem = driver.find_element(By.ID, "tab0-0")
    elem.click()
    jobs_div_elem = driver.find_element(By.ID, "panel0-0")
    jobs = jobs_div_elem.find_elements(By.CLASS_NAME, "careers__results-job")
    remote_jobs = []

    for job in jobs:
        link_elem = job.find_element(By.CLASS_NAME, "careers__results-job-link")
        location_elem = job.find_element(
            By.CLASS_NAME, "careers__results-job-link-text"
        )
        remote_job = {}
        remote_job["location"] = location_elem.text
        remote_job["title"] = link_elem.text
        remote_job["link"] = link_elem.get_property("href")
        remote_jobs.append(remote_job)

    driver.close()

    return remote_jobs


def get_job_diffs():
    prev_db = TinyDB("prev_jobs.db")
    db = TinyDB("jobs.db")
    db.drop_tables()

    remote_jobs = get_job_postings()
    db.insert_multiple(remote_jobs)

    prev_db_jobs = prev_db.all()
    new_db_jobs = db.all()

    diff = DeepDiff(prev_db_jobs, new_db_jobs)

    added = diff.get("iterable_item_added", {}).values()
    removed = diff.get("iterable_item_removed", {}).values()

    prev_db.drop_tables()
    prev_db.insert_multiple(remote_jobs)

    return {"added": added, "removed": removed}


def convert_jobs_dict_to_str(jobs):
    string_job = ""
    for job in jobs:
        string_job += f"{job['title']}: {job['link']}\n"
    return string_job


def send_notification(jobs):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    added_string_jobs = "Added: "
    removed_string_jobs = "Removed: "

    added_jobs = jobs["added"]
    removed_jobs = jobs["removed"]

    added_string_jobs += convert_jobs_dict_to_str(added_jobs)
    removed_string_jobs += convert_jobs_dict_to_str(removed_jobs)

    if len(added_string_jobs) > len("Added: "):
        conn.request(
            "POST",
            "/1/messages.json",
            urllib.parse.urlencode(
                {
                    "token": os.getenv("PUSHOVER_TOKEN"),
                    "user": os.getenv("PUSHOVER_USER"),
                    "message": added_string_jobs,
                }
            ),
            {"Content-type": "application/x-www-form-urlencoded"},
        )
        conn.getresponse()

    if len(removed_string_jobs) > len("Removed: "):
        conn.request(
            "POST",
            "/1/messages.json",
            urllib.parse.urlencode(
                {
                    "token": os.getenv("PUSHOVER_TOKEN"),
                    "user": os.getenv("PUSHOVER_USER"),
                    "message": removed_string_jobs,
                }
            ),
            {"Content-type": "application/x-www-form-urlencoded"},
        )
        conn.getresponse()


def main():
    jobs = get_job_diffs()
    send_notification(jobs)


main()
