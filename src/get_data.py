from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located

#icao_codes = ["KTKI", "KDAL"]

def selenium_metar(codes: list):
    driver = webdriver.Chrome("F:\metar-board\src\drivers\chromedriver.exe")
    ids_box = '//*[@id="bottom_right"]/form[1]/div[1]/input'
    submit_button = '//*[@id="bottom_right"]/form[1]/div[5]/input'
    url = "https://www.aviationweather.gov/metar"

    icao_string = ""
    for code in codes:
        icao_string += code + ","
    icao_string = icao_string[:-1]

    driver.get(url)
    driver.find_element_by_xpath(ids_box).send_keys(icao_string)
    driver.find_element_by_xpath(submit_button).click()

    output_data = []
    if len(codes) != 1:
        for i in range(len(codes)):
            metar_data = f'//*[@id="awc_main_content_wrap"]/code[{i+1}]'
            metar_data = driver.find_element_by_xpath(metar_data).text
            output_data.append(metar_data)
    else:
        metar_data = f'//*[@id="awc_main_content_wrap"]/code'
        metar_data = driver.find_element_by_xpath(metar_data).text
        output_data.append(metar_data)

    driver.quit()
    return output_data


def update_data(type: str, codes: list):
    match type:
        case "selenium":
            data = selenium_metar(codes)
    return data

if __name__ == "__main__":
    codes = [
        "KTKI",
        "KDTO",
        "KDFW",
        "KDAL",
        "KHQZ",
        "KFWS",
        "KFTW",
        "KAFW",
        "KRBD",
        "KGKY",
    ]
    data = update_data("selenium", codes)
    print(data)
