# -*- coding: utf-8 -*-
"""
Created on Mon Jun  6 12:31:24 2022

@author: Adrian
"""
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import random
import datetime as dt
import sys
#os.chdir('D:\\Python\\Others') #change accordingly
from Functions_Rental_Car_Alert import *

time.sleep(1)
#Set the variables

if len(sys.argv) > 1: #limit is the first argument when executing the script. otherwise it is set as a default value
    limit = float((sys.argv[1]).replace('€', '').replace(',', '.'))
else:
    limit = 115

print('Limit set as: ', limit, '€')


insurance_limit = True
only_cancelable = True
headless = True

if insurance_limit:
    insurance_ratio = 0.9
else:
    insurance_ratio = 1

emailadress = 'adrianalvarez3091@gmail.com'
# url = 'https://www.doyouspain.com/do/list/es?s=b9b3e103-550c-4906-9605-3c955c54a5ec&b=8068a369-e8b1-44f0-8ae9-a8cae11e9881'
# url = 'https://www.doyouspain.com/do/list/es?s=c14f6ece-c8c9-4248-be13-ea43804a184a&b=8068a369-e8b1-44f0-8ae9-a8cae11e9881'
# url= 'https://www.doyouspain.com/do/list/es?s=7c8c5644-e508-43b6-9d99-b3c307866fb2&b=272cdc63-8e35-46b8-93c8-1e44fdae0d31'
url = 'https://www.doyouspain.com/do/list/en?s=2462574f-b111-44de-96f1-97593639bfe5&b=b48c7095-3007-474c-94dd-91a3e451a67f'
options = create_options_selenium(headless=headless)


old_results = 0


while True:
    try:
        print('... Searching in DoyouSpain...')
        text = ''
        email = False
        browser = webdriver.Chrome(options=options)#open headless chrome1
        browser.get(url)
        time.sleep(1)
        try:
            # Locate the "Aceptar todas las cookies" button using its ID
            accept_cookies_button = browser.find_element(By.ID, "checkAllOptions")
            
            # Click the button to accept cookies
            accept_cookies_button.click()
            time.sleep(1)
            print("Cookies accepted.")

        except Exception as e:
            print(f"Error: {e}")

        try:
            print('...Searching for cars...')
            search_button = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '#idSearchButton button#sendForm'))
            )
            search_button.click()
            time.sleep(5)
        
        except Exception as e:
            print(f"Error searching and locating search button: {e}")            
        
        title_options = ["Full/Full", "Lleno/Lleno"]

        fuel_option = None

        # Iterate through title options to find the first clickable element
        for title in title_options:
            try:
                time.sleep(1)
                fuel_option = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f'.fuel-option.fuel-option-none.tooltipBlancoBig[title*="{title}"]'))
                )
                if fuel_option:
                    fuel_option.click()
                    print(f"Clicked on fuel option with title: {title}")
                    break
            except Exception as e:
                print(f"Option with title '{title}' not found or not clickable. Trying next...")
                        
        time.sleep(3)
        if only_cancelable:
            try:
                cancel_option = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.ID, 'idCancel1'))
                )
                
                # Click the radio button if it's present
                cancel_option.click()
                print("Only cancelable cars selected.")
            
            except Exception as e:
                print(f"Error: {e}")
        time.sleep(3)

        page_source = browser.page_source
        soup = BeautifulSoup(page_source, features="lxml")
        #find a list of each soup per car:
        soups = get_car_soups(soup)
        results = {}
        for n, car in enumerate(soups):
            results[n] = get_info_car(car, n, limit)
        filtered_results ={}
        # print(results)
        for nn, result in enumerate(results.values()):
            print(result[4], result[0], 'limit:',limit*insurance_ratio)
            if (result[0]< limit*insurance_ratio) and result[4] != 'Lleno/Vacío (Dev.)':
                print('checking insurance price...')
                filtered_results[nn] = result
                time.sleep(1)
                element = browser.find_element(By.CLASS_NAME,"bdg-container")
                # Execute JavaScript code to set the element's style attribute to "display:none"
                browser.execute_script("arguments[0].style.display='none'", element)
                WebDriverWait(browser, 90).until(EC.element_to_be_clickable((By.NAME,str('coche'+str(nn+1))))).click()
                new_page_source = browser.page_source
                newsoup = BeautifulSoup(new_page_source, features="lxml")
                insurance_price = get_insurance_price(newsoup, result[0])
                filtered_results[nn] += [insurance_price]
                browser.back()
                if isinstance(insurance_price, float) and insurance_price > limit:
                    print('Insurance price is higher than the limit, stopping search...')
                    break
        
        browser.close()
        if insurance_limit:
            email_results = {}
            for result in filtered_results:
                if filtered_results[result][-1] < limit:
                    email_results[result] = filtered_results[result]
        else:
            email_results = filtered_results
        email = True if len(email_results) > 0 and str(old_results).replace("'","").replace('"', '') != str(email_results).replace("'","").replace('"', '')  else False
        old_results = email_results.copy()
        if email:
            print(len(email_results), 'results found under the setted price')
            subject = str(len(email_results)) + ' Car(s) at lower price in DoyouSpain'
            text = email_text_generator(email_results, insurance_limit, limit, url)
            sendedmail = sendemail(emailadress, subject, text)
            if sendedmail:
                print('...Email sent...')
                sendedmail = False
            # conn.quit()     
        elif len(email_results) < 1:
            print("No cars found cheaper than", limit, '€')
        else:
            print('Results have been already notified by email in the previous lookup')
        waitingfor = 60*60*random.uniform(0.7, 0.9)*1
        print("Waiting for next round: ", waitingfor/60/60)
        now = dt.datetime.now()
        t1 = dt.datetime.strptime(str(now.hour)+':'+str(now.minute) +':0', '%H:%M:%S')
        t2 = dt.datetime.strptime(str(int(waitingfor/3600))+':'+str(int((waitingfor/3600 % 1*60))) +':0', '%H:%M:%S')
        time_zero = dt.datetime.strptime('00:00:00', '%H:%M:%S')
        print('Next search programmed at:',(t1 - time_zero + t2).time())
        time.sleep(waitingfor)
    
    except Exception as e:
        print(f"Whole pipeline Error: {e}")
        try:
            browser.close()
        except:
            pass
        time.sleep(60*5)
        continue

