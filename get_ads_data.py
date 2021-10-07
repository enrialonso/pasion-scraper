from concurrent.futures import ThreadPoolExecutor as PoolExecutor
from datetime import datetime as dt

from playwright.sync_api import Playwright, sync_playwright, TimeoutError

from models.models import Categories, Cities
from utils.utils import create_sql_session, get_data_ad_load_on_table
from sqlalchemy.exc import OperationalError
from models.models import create_db
from get_categories_and_cities import main as get_categories_and_cities

scraping_date = dt.now()


def run(playwright: Playwright, config) -> None:
    session = create_sql_session()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.pasion.com/")
    page.click("text=Contactos hombres")
    page.click("text=ENTRAR")

    print(f"Select category: {config['category']}, city: {config['city']}")
    categories_select = page.query_selector("//*[@id='ca2']")
    categories_select.select_option(value=config["category"])
    page.wait_for_timeout(500)

    city_select = page.query_selector("//*[@id='protmp']")
    city_select.select_option(value=config["city"])
    page.query_selector("//*[@id='vamos']/div").click()
    page.wait_for_timeout(1000)

    index = 0
    while True:
        get_data_ad_load_on_table(page, session, config["category"], config["city"], scraping_date)
        try:
            button = page.wait_for_selector("td >> div >> a:text('Siguiente')", timeout=500)
            button.click()
        except TimeoutError:
            break
        index += 1
        if index == 6:
            break

    context.close()
    browser.close()


def worker(config):
    with sync_playwright() as playwright:
        run(playwright, config)


def main():
    session = create_sql_session()
    config_workers = []
    try:
        data = session.query(Categories).all()
    except OperationalError:
        create_db()
        get_categories_and_cities()
        data = session.query(Categories).all()

    for category in data:
        for city in session.query(Cities).all():
            if category.value and city.value:
                config_workers.append({"category": category.value, "city": city.value})

    with PoolExecutor(max_workers=5) as executor:
        for _ in executor.map(worker, config_workers):
            pass


if __name__ == "__main__":
    main()
