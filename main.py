import shutil
import threading
import queue
import urllib.error

from bs4 import BeautifulSoup
from urllib import request
from pathlib import Path

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
BANNED_IMAGES = ["/img/valid-xhtml10.gif", "/img/valid-css.gif", "/img/vim.gif"]
BASE_URL = "http://pt.jikos.cz"
GARFIELD_URL = "http://pt.jikos.cz/garfield/"
BASE_DIR = "./garfield"
WORKER_THREADS = 32

PRINT_LOCK = threading.Lock()


def read_url(url: str):
    """
    Reads a URL and returns the string representation of that webpage.

    :param url: The url you want to read.
    :return: The web page in String format.
    """
    file = request.urlretrieve(url)

    text = ""
    with open(file[0], 'r') as contents:
        for line in contents.readlines():
            text += line
    return text


def get_soup(file_contents):
    """
    :param file_contents: Some HTML in String format
    :return: A bs4 representation of that webpage
    """
    return BeautifulSoup(file_contents, features='html.parser')


def find_images_on_page(page: BeautifulSoup):
    """
    :param page: The bs4 page you want to search for images.
    :return: A filtered list of images in bs4 format.
    """
    images = page.find_all('img')
    images = list(filter(lambda x: str(x['src']).endswith("gif") and x['src'] not in BANNED_IMAGES, images))
    return images


def parse_date(_datestr: str):
    """
    :param _datestr: A European-Style date, example: 24/3/2021
    :return: a 3-tuple of (day, month, year)
    """
    spl = _datestr.split('/')
    return int(spl[0]), int(spl[1]), int(spl[2])


def download_image(image: BeautifulSoup):
    """
    Parses some bs4 image tag to download the image that is mentioned in it, and
    saves it in the right directory.

    :param image: The image in bs4 format you want to download.
    """
    image_url = image['src']
    alt_text = image['alt']
    _, datestring = alt_text.split(' ')
    day, month, year = parse_date(datestring)

    month_dir = f"{BASE_DIR}/{year:02d}/{month:02d}"
    target_dir = month_dir
    target_name = f"{day:02d}.gif"
    full_file_path = f"{target_dir}/{target_name}"

    if not Path.exists(Path(full_file_path)):
        s_print(f"Downloading file {full_file_path}... ({q.qsize()} in queue)")
        Path.mkdir(Path(month_dir), exist_ok=True)
        try:
            image_file, _ = request.urlretrieve(image_url)
            shutil.move(image_file, full_file_path)
        except urllib.error.HTTPError | urllib.error.HTTPError:
            s_print(f"File {full_file_path} not found!")

    else:
        s_print(f"Skipping file {full_file_path} (already exists).")


def download_all_images_in(collection):
    for image in collection:
        download_image(image)


def add_images_to_queue(collection):
    """Adds a collection of images to the working queue."""
    for image in collection:
        q.put(image)


def worker():
    """The method that is called in the worker threads."""
    while True:
        image = q.get()
        download_image(image)
        q.task_done()


def s_print(*args, **kwargs):
    """
    Thread safe printer.

    Source: https://stackoverflow.com/a/50882022
    """
    with PRINT_LOCK:
        print(*args, **kwargs)


if __name__ == '__main__':
    q = queue.Queue()

    threads = []
    for i in range(WORKER_THREADS):
        threads.append(threading.Thread(target=worker, daemon=True))
    for th in threads:
        th.start()

    base_soup = get_soup(read_url(GARFIELD_URL))
    year_links = base_soup.find_all('a')
    year_links = list(filter(lambda lin: "garfield/" in str(lin), year_links))

    s_print(f"Found {len(year_links)} years.")

    Path.mkdir(Path(BASE_DIR), exist_ok=True)

    for year_link in year_links:
        year = year_link.string
        Path.mkdir(Path(f"{BASE_DIR}/{year}"), exist_ok=True)

        first_month_page = get_soup(read_url(BASE_URL + year_link['href']))

        first_month_images = find_images_on_page(first_month_page)
        add_images_to_queue(first_month_images)

        # extract all other months
        other_month_links = list(first_month_page.find_all('a'))
        other_month_links = list(filter(lambda x: x.string in MONTHS, other_month_links))

        for other_month_link in other_month_links:
            other_month_page = get_soup(read_url(BASE_URL + other_month_link['href']))
            other_month_images = find_images_on_page(other_month_page)
            add_images_to_queue(other_month_images)

    original_q_size = q.qsize()

    q.join()

    print("I hate Mondays!")
