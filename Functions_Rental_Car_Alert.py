import re
from selenium import webdriver
import smtplib
def email_text_generator(email_results, insurance_limit, limit, url):
    """
    Generates an email text summarizing car rental results under a price limit.
    
    Parameters:
    - email_results (dict): Dictionary containing car rental data.
    - insurance_limit (bool): Whether the limit applies to insurance price or not.
    - limit (float): The price limit for the rentals.
    - url (str): URL to include in the email.
    
    Returns:
    - str: Generated email text.
    """
    # Initialize the email text with a summary header
    text = f"{len(email_results)} RESULTS UNDER LIMIT PRICE! ({limit}€)\n\n"
    
    # Iterate over car results to build the details
    for car, details in email_results.items():
        try:
            # Calculate the discount based on the limit and price
            if insurance_limit:
                discount = round(limit - float(details[-1]), 2)
            else:
                discount = round(limit - float(details[0]), 2)
            
            # Ensure all details are strings for consistent formatting
            details = [str(detail) for detail in details]
            
            # Replace newlines outside the f-string
            feature_description = details[5].replace('\n', ' ')
            
            # Construct the line for the current car
            line = (
                f"Discount of {discount}€!! "
                f"{details[7]} doors car model: {details[6]} found at {details[-1]}€ with insurance "
                f"({details[0]}€ without) with the company {details[1]}. The car includes: {details[3]} and "
                f"{feature_description}. The pickup is: {details[2]}.\n\n"
            )
            text += line
        except (IndexError, ValueError, TypeError) as e:
            # Handle any unexpected issues with car details
            text += f"Error processing car {car}: {e}\n\n"
    
    # Append the URL to the email text
    text += f"\n\n{url}"
    
    # Return the generated email text
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
    options.add_argument('--window-size=1920x1080')
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage") ## overcome limited resource problems
    options.add_argument("--no-sandbox")
    if headless:
        # print("Headless mode Selenium")
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


def get_info_car(car,n, limit):
    price = get_car_price(car)
    company=car.find_all('span',{"class": "cl--car-rent-info"})[0].getText().replace(" Condiciones", "")

    company_element = car.select_one('.cl--car-rent-logo img')
    if company_element and company_element.has_attr('alt'):
        company = company_element['alt']
    else:
        company = 'Unknown'
        print("Company name not found.")
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
    # if price < limit:
        # print(price, 'Euros', "at", company, shuttle, milelimit, gasolin, policy, car_model)
    doors_element = car.find('li', class_='tooltipBlanco serv sc-doors')
    if doors_element:
        number_of_doors = doors_element.text.strip()
    else:
        number_of_doors = 'Unknown'
    return [price, company, shuttle, milelimit, gasolin, policy, car_model, number_of_doors]

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




# def sendemail(email, subject, text):
#     conn=smtplib.SMTP('smtp-mail.outlook.com',587)
#     type(conn)
#     conn.ehlo()
#     conn.starttls()
#     conn.login('flatronlg@hotmail.es','flatronL1915s+')
#     finaltext = ('Subject: ' +subject + '\n\n' + text).encode("utf-8")
#     conn.sendmail('flatronlg@hotmail.es',email,finaltext )
#     conn.quit()  
#     return True
def sendemail(email, subject, text):
    # Set up Gmail SMTP server
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'rent.a.car.alert@gmail.com'  # Replace with your Gmail address
    sender_password = 'qskg gkzg dpjg gxqg'  # Replace with your Gmail app password
    
    try:
        # Create connection
        conn = smtplib.SMTP(smtp_server, smtp_port)
        conn.ehlo()
        conn.starttls()
        
        # Log in to the server
        conn.login(sender_email, sender_password)
        
        # Format the email content
        final_text = f"Subject: {subject}\n\n{text}"
        
        # Send the email
        conn.sendmail(sender_email, email, final_text.encode("utf-8"))
        
        # Close the connection
        conn.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# sendemail('adrian_3091@hotmail.com', 'Test', 'This is a test')





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