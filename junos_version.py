#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest",
#   "selenium",
# ]
# ///

from selenium import webdriver  # pyright: ignore[reportMissingImports]


def main() -> None:
    """foo"""

    driver = webdriver.Chrome("/opt/homebrew/bin/chromedriver")

    # Open the Python website
    driver.get("https://www.python.org")

    # Print the page title
    print(driver.title)

    # Find the search bar using its name attribute
    # search_bar = driver.find_element_by_name("q")
    # search_bar.clear()
    # search_bar.send_keys("getting started with python")
    # search_bar.send_keys(Keys.RETURN)

    # Print the current URL
    print(driver.current_url)

    driver.quit()


if __name__ == "__main__":
    main()
