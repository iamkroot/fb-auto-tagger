import re
import time

from fuzzywuzzy import fuzz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (ElementNotInteractableException,
                                        StaleElementReferenceException,
                                        TimeoutException)
import pytoml


def read_config(path="config.toml"):
    with open(path) as f:
        config = pytoml.load(f)

    def read_info_files(param):
        with open(config['INFO'][param]) as f:
            names = f.read().split('\n')
            config['INFO'][param] = [name for name in names if name]
    read_info_files('names')
    read_info_files('exclude')
    return config


def start_driver(profile_path=None):
    if profile_path:
        print("Using profile at", profile_path)
    fp = profile_path and webdriver.FirefoxProfile(profile_path) or None
    print(fp)
    return webdriver.Firefox(firefox_profile=fp)


BASE_URL = 'https://facebook.com/'
config = read_config()
driver = start_driver(config['BROWSER'].get('profile_path'))


def login(username, password):
    driver.get(BASE_URL)
    driver.find_element_by_id('email').send_keys(username)
    driver.find_element_by_id('pass').send_keys(password)
    driver.find_element_by_id('loginbutton').click()


def open_post(group_name, permalink_num):
    driver.get(f'{BASE_URL}groups/{group_name}/permalink/{permalink_num}')


def get_comment_box(permalink_num, timeout=60):
    commentbox_id = 'addComment_' + str(permalink_num)
    comment_box = WebDriverWait(driver, timeout).until(
        ec.presence_of_element_located((By.ID, commentbox_id)))
    return comment_box


def get_comment_div(comment_box, timeout=60):
    comment_box.click()
    comment_xpath = 'div/div[2]/div/div/div/div/div/div/div/div[2]/div'
    comment = WebDriverWait(comment_box, timeout).until(
        ec.presence_of_element_located((By.XPATH, comment_xpath)))
    return comment


def get_author():
    div1 = driver.find_element_by_css_selector('div._4r_y ~ div h5')
    return div1.text.strip()


def get_seen(permalink_num):
    seen_url = f'{BASE_URL}ufi/group/seenby/profile/browser/?id='
    driver.get(f"{seen_url}{permalink_num}")
    try:
        see_more = WebDriverWait(driver, 10).until(
            ec.presence_of_element_located((By.ID, 'group_seen_by_pager_seen'))
        )
    except (ElementNotInteractableException, TimeoutException):
        return
    fetch_tag = see_more.find_element_by_tag_name('a')
    fetch_url = fetch_tag.get_attribute('href')
    new_url = re.sub(r'limit=[0-9]+', 'limit=1000', fetch_url)
    script = f"arguments[0].setAttribute('href','{new_url}')"
    driver.execute_script(script, fetch_tag)
    see_more.click()
    time.sleep(2)
    seen_tab = driver.find_element_by_id('groups_seen_by_profile_browser_seen')
    name_xpath = 'div/div/div/div[2]/div[2]/div/a'
    seen = set()
    for person in seen_tab.find_elements_by_tag_name('li'):
        seen.add(person.find_element_by_xpath(name_xpath).text)
    return seen


def tag_person(name, comment):
    comment.send_keys('@' + name)
    comment.send_keys(Keys.ARROW_LEFT)
    time.sleep(0.1)
    comment.send_keys(Keys.ARROW_RIGHT)
    time.sleep(0.3)
    try:
        popup = WebDriverWait(driver, 10).until(ec.presence_of_element_located(
            (By.CSS_SELECTOR, "ul[role='listbox']")
        ))
    except TimeoutException:
        return -1
    popup_names = popup.find_elements_by_tag_name('li')
    popup_names.pop(0)
    for li in popup_names:
        popup_name = li.get_attribute('aria-label')
        if not popup_name:
            continue
        popup_name = popup_name.strip()
        if popup_name == 'No results':
            return 0
        if fuzz.ratio(popup_name, name) > 90:
            time.sleep(0.01)
            li.find_element_by_xpath('div/div[2]/div').click()
            time.sleep(0.05)
            return popup_name


def tag_in_one_comment(comment_box, names, exclude):
    comment = get_comment_div(comment_box)
    for name in names:
        if exclude and name in exclude:
            continue
        try:
            result = tag_person(name, comment)
        except StaleElementReferenceException:
            comment = get_comment_div(comment_box)
            result = tag_person(name, comment)
        if isinstance(result, int) and result <= 0:
            print("Timed out for" if result else "No results for", name)
            comment.send_keys(Keys.SHIFT + Keys.HOME)
            comment.send_keys(Keys.BACKSPACE)
            time.sleep(1)
        else:
            print("Tagged", result)
            comment.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(0.1)


def tag_all(permalink_num, names, tags_per_comment=15, exclude=None):
    comment_box = get_comment_box(permalink_num)
    n = tags_per_comment
    for i in range(0, len(names), n):
        tag_in_one_comment(comment_box, names[i:i + n], exclude)


def main():
    login(**config['CREDS'])
    excludes = config['INFO']['exclude']
    print(config)
    if config['INFO']['exclude_seen']:
        print("Excluding those who have already seen post.")
        excludes.extend(get_seen(config['FB']['permalink_num']) or [])
    open_post(config['FB']['group_name'], config['FB']['permalink_num'])
    print("Excluding author")
    excludes.append(get_author())
    tag_all(config['FB']['permalink_num'], config['INFO']['names'],
            config['FB']['tags_per_comment'], excludes)


if __name__ == '__main__':
    main()
