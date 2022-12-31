# -*- coding: utf-8 -*-
"""
Created on Mon Jun  6 12:31:24 2022

@author: Adrian
"""
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import smtplib  
import re
import time
import random
import datetime as dt
import os
#os.chdir('D:\\Python\\Others') #change accordingly
from Functions_Rental_Car_Alert import *


#Set the variables
limit = 55.66
insurance_limit = True
emailadress = 'adrianalvarez3091@gmail.com'
url = 'https://www.doyouspain.com/do/list/es?s=72cc3ec4-9522-4a4a-b38a-a07fbe9409a2&b=63025388-6c36-4340-9996-fba1ff959e6c'


options = create_options_selenium(True)


stop = False
old_results = 0


while stop == False:
    print('... Searching in DoyouSpain...')
    text = ''
    email = False
    browser = webdriver.Chrome(options=options)#open headless chrome1
    browser.get(url)
    page_source = browser.page_source
    soup = BeautifulSoup(page_source, features="lxml")
    #find a list of each soup per car:
    soups = get_car_soups(soup)
    results = {}
    for n, car in enumerate(soups):
        results[n] = get_info_car(car, n)
    filtered_results ={}
    for nn, result in enumerate(results.values()):
        if (result[0]< limit) and result[4] != 'Lleno/Vacío (Dev.)':
            filtered_results[nn] = result
            time.sleep(1)
            element = browser.find_element(By.CLASS_NAME,"bdg-container")
            # Execute JavaScript code to set the element's style attribute to "display:none"
            browser.execute_script("arguments[0].style.display='none'", element)
            WebDriverWait(browser, 90).until(EC.element_to_be_clickable((By.NAME,str('coche'+str(nn+1))))).click()
            new_page_source = browser.page_source
            newsoup = BeautifulSoup(new_page_source, features="lxml")
            filtered_results[nn] += [get_insurance_price(newsoup, result[0])]
            browser.back()
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
    waitingfor = 60*60*random.uniform(0.7, 0.9)*2
    print("Waiting for next round: ", waitingfor/60/60)
    now = dt.datetime.now()
    t1 = dt.datetime.strptime(str(now.hour)+':'+str(now.minute) +':0', '%H:%M:%S')
    t2 = dt.datetime.strptime(str(int(waitingfor/3600))+':'+str(int((waitingfor/3600 % 1*60))) +':0', '%H:%M:%S')
    time_zero = dt.datetime.strptime('00:00:00', '%H:%M:%S')
    print('Next search programmed at:',(t1 - time_zero + t2).time())
    time.sleep(waitingfor)

