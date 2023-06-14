import re
from selenium import webdriver
import smtplib

def email_text_generator(email_results, insurance_limit, limit, url):
    text = str(len(email_results)) + ' RESULTS UNDER LIMIT PRICE! (' + str(limit) + '€) \n\n'
    for car in email_results:
        t = email_results[car]
        if insurance_limit:
            discount = round(limit - float(t[-1]),2)
        else:
            discount = round(limit - float(t[0]), 2)
        for n, tt in enumerate(t):
            t[n] = str(tt)
        line = 'Discount of ' + str(discount) + "!! "
        line += t[6] +' found at ' + t[-1] + '€ with insurance (' + t[0] + '€ without) with the company ' + t[1]+'. The car includes: ' + t[3] + ' and ' + t[5].replace('\n', ' ') + '. The pickup is: ' + t[2] +'\n\n'
        text += line
    print(text)
    text += '\n\n'+url
    return text   




def create_options_selenium(headless = True):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "plugins.always_open_pdf_externally": True,
    })
    options.add_argument('ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('window-size=1920x1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage") ## overcome limited resource problems
    options.add_argument("--no-sandbox")
    if headless:
        print("Headless mode Selenium")
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options

def get_car_soups(soup):
    soups = []
    for p in soup.find_all('section',{"class": "newcarlist price-per-day"}):
        for element in p:
            if str(element).startswith('<article'):
                soups.append(element)
    return soups

def get_car_price(car):
    price = ""
    for p in car.find_all('span',{"class": "price pr-euros green special-price"}):
        for pp in p:
            for match in (re.findall(r'[0-9.]', pp)):
                price += match 
    if price == "":
        for p in car.find_all('span',{"class": "price pr-euros"}):
            for pp in p:
                for match in (re.findall(r'[0-9.]', pp)):
                    price += match
    return float(price)       


def get_info_car(car,n):
    price = get_car_price(car)
    company=car.find_all('span',{"class": "cl--car-rent-info"})[0].getText().replace(" Condiciones", "")
    shuttle= car.find_all('li',{"class": "tooltipBlanco serv sc-airport"})[0].getText()
    milelimit = car.find_all('li', {"class": "tooltipBlanco serv sc-mileage sc-green"})
    if len(milelimit) > 0:
        milelimit = milelimit[0].getText()
    else:
        milelimit = 'Unknown'
    gasolin = car.find_all('span', {"class": "udl-block"})[0].getText()
    policy = car.find_all('ul', {"class": "cl--interest"})[0].getText()#.replace("\n", "\s" )
    car_model = car.find_all('div', {"class": "cl--name"})[0].find_all('h2')[0].getText()
    if len(policy) <3:
        policy = 'Not Refundable'
    print(price, 'Euros', "at", company, shuttle, milelimit, gasolin, policy, car_model)
    return [price, company, shuttle, milelimit, gasolin, policy, car_model]

def get_insurance_price(newsoup, original_price):
    global email_results
    insuranceprice = ''
    for price in newsoup.find_all('td', {"data-for": "insurance"}):
            if "Alquiler + Seguro" in (price.getText()):
                for match in (re.findall(r'[0-9.]', price.getText())):
                    insuranceprice += match
    if len(insuranceprice) >0:
        return(float(insuranceprice))
    else:
        startc = str(newsoup).find('var cAux = ')
        starti = str(newsoup).find('var iAux = ')
        insurancepricec = float(str(newsoup)[startc+11:str(newsoup).find(';',startc)])
        insurancepricei = float(str(newsoup)[starti+11:str(newsoup).find(';',starti)])
        if insurancepricec > 0:
            return (original_price + +float(insurancepricec))
        elif insurancepricei > 0:
            return (original_price + +float(insurancepricei))
        else:
            return 'Could not find it'




def sendemail(email, subject, text):
    conn=smtplib.SMTP('smtp-mail.outlook.com',587)
    type(conn)
    conn.ehlo()
    conn.starttls()
    conn.login('flatronlg@hotmail.es','2344Alva+')
    finaltext = ('Subject: ' +subject + '\n\n' + text).encode("utf-8")
    conn.sendmail('flatronlg@hotmail.es','adrianalvarez3091@gmail.com',finaltext )
    conn.quit()  
    return True







# def sendemail(email, subject, text):
#     url='https://login.live.com/login.srf?wa=wsignin1.0&rpsnv=13&ct=1654596384&rver=7.0.6737.0&wp=MBI_SSL&wreply=https%3a%2f%2foutlook.live.com%2fowa%2f0%2f%3fstate%3d1%26redirectTo%3daHR0cHM6Ly9vdXRsb29rLmxpdmUuY29tL21haWwvMC8%26nlp%3d1%26RpsCsrfState%3d7e3e27af-c0c3-0527-099c-79a7ab9cf2bd&id=292841&aadredir=1&CBCXT=out&lw=1&fl=dob%2cflname%2cwld&cobrandid=90015'
#     browser = webdriver.Chrome(options=options)#open headless chrome1
#     browser.get(url)
#     time.sleep(3)
#     search_form = browser.find_element(By.ID,'i0116')
#     search_form.send_keys('flatronlg@hotmail.es')
#     time.sleep(1)
#     buttom = browser.find_element(By.ID, 'idSIButton9')
#     buttom.click()
#     time.sleep(1)
#     search_form2 = browser.find_element(By.ID,'i0118')
#     search_form2.send_keys('L1915s+L1915s+')
#     buttom = browser.find_element(By.ID, 'idSIButton9')
#     buttom.click()
#     time.sleep(3)
#     buttom = browser.find_element(By.ID, 'idBtn_Back')
#     buttom.click()
#     time.sleep(5)
#     #Send Email
#     sendemail = browser.find_element(By.ID, 'id__9')
#     sendemail.click()
#     time.sleep(5)
#     # page_source = browser.page_source
#     # recipient = browser.find_element(By.CLASS_NAME, 'ms-BasePicker-input')
#     recipient = browser.find_element(By.CLASS_NAME, 'QdX2d')
    
#     recipient.send_keys(email)
#     # asunto = browser.find_element(By.ID, 'TextField238')
#     asunto = browser.find_element(By.CLASS_NAME, 'ms-TextField-field')
    
#     asunto.send_keys(subject)
#     textElem = browser.find_element(By.CLASS_NAME, 'dbf5I')
#     textElem.send_keys(text)
#     time.sleep(3)
#     sendElem = browser.find_element(By.CLASS_NAME, 'ms-Button.ms-Button--primary.ms-Button--hasMenu')
#     sendElem.click()
#     time.sleep(5)
#     browser.close()
#     return True