import shutil
import threading

from bs4 import BeautifulSoup
from urllib import request
from pathlib import Path
from shutil import rmtree

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
BANNED_IMAGES = ["/img/valid-xhtml10.gif", "/img/valid-css.gif", "/img/vim.gif"]
BASE_URL = "http://pt.jikos.cz"
GARFIELD_URL = "http://pt.jikos.cz/garfield/"
BASE_DIR = "./garfield"


def read_url(url: str):
    file = request.urlretrieve(url)

    text = ""
    with open(file[0], 'r') as contents:
        for line in contents.readlines():
            text += line
    return text


def get_soup(file_contents):
    return BeautifulSoup(file_contents, features='html.parser')


def find_images_on_page(page: BeautifulSoup):
    images = page.find_all('img')
    images = list(filter(lambda x: str(x['src']).endswith("gif") and x['src'] not in BANNED_IMAGES, images))
    return images


def parse_date(_datestr: str):
    spl = _datestr.split('/')
    return int(spl[0]), int(spl[1]), int(spl[2])


def download_image(imageurl, target_name, target_dir):
    full_file_path = f"{target_dir}/{target_name}"

    if not Path.exists(Path(full_file_path)):
        print(f"Downloading file {full_file_path}...")
        image_file, _ = request.urlretrieve(imageurl)
        shutil.move(image_file, full_file_path)
    else:
        print(f"Skipping file {full_file_path} (already exists).")


def download_all_images_in(collection):
    for image in collection:
        image_url = image['src']
        alt_text = image['alt']
        _, datestring = alt_text.split(' ')
        day, month, year = parse_date(datestring)

        month_dir = f"{BASE_DIR}/{year:02d}/{month:02d}"

        Path.mkdir(Path(month_dir), exist_ok=True)
        download_image(image_url, f"{day:02d}.gif", month_dir)


if __name__ == '__main__':
    base_soup = get_soup(read_url(GARFIELD_URL))
    year_links = base_soup.find_all('a')
    year_links = list(filter(lambda lin: "garfield/" in str(lin), year_links))

    print(f"Found {len(year_links)} links")

    # rmtree(BASE_DIR)
    Path.mkdir(Path(BASE_DIR), exist_ok=True)

    for year_link in year_links:
        year = year_link.string
        Path.mkdir(Path(f"{BASE_DIR}/{year}"), exist_ok=True)

        first_month_page = get_soup(read_url(BASE_URL + year_link['href']))

        # the images now have have the following format:
        #   <img alt="garfield 19/6/1978" src="http://images.ucomics.com/comics/ga/1978/ga780619.gif"/>
        first_month_images = find_images_on_page(first_month_page)
        threading.Thread(target=download_all_images_in, args=(first_month_images,)).start()
        # download_all_images_in(first_month_images)

        # extract all other months
        other_month_links = list(first_month_page.find_all('a'))
        other_month_links = list(filter(lambda x: x.string in MONTHS, other_month_links))

        for other_month_link in other_month_links:
            other_month_page = get_soup(read_url(BASE_URL + other_month_link['href']))
            other_month_images = find_images_on_page(other_month_page)
            threading.Thread(target=download_all_images_in, args=(other_month_images,)).start()
