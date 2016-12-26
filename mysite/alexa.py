from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
from datetime import datetime
import requests
import urllib
import re
import random

# --------------------------------------------------------------------------------------------
# INITIALISATION

app = Flask(__name__)
ask = Ask(app, "/alexa")

@ask.launch
def new_ask():
    welcome = render_template('welcome')
    reprompt = render_template('reprompt')
    return question(welcome) \
        .reprompt(reprompt)

# --------------------------------------------------------------------------------------------
# 1) IGN REVIEW APPLICATION

@ask.intent('ReviewLatestIntent')
def launchReview(show):
    if (show is None):
        reprompt_show = render_template("reprompt_show")
        return question(reprompt_show)
    else:
        filShow = processShowName(show)
        latest = getLatestReview(filShow)
        review_title = latest["searchitem_link_2/_text"]
        episode_title = review_title.split(':')[1].replace('"','')
        if (" Review" in episode_title):
            episode_title = episode_title.replace(" Review", "")
        image_url = latest["searchitem_image"].replace("_160w", "_480w").replace("http", "https")
        score = str(latest["reviewscore_number"])
        description = latest["ignreview_description"]
        latestReview_msg = render_template('latest_review', show=show, episode=episode_title, score=score)
        return statement(latestReview_msg) \
            .standard_card(title=review_title + " - " + score,
                            text=description,
                            small_image_url=image_url,
                            large_image_url=image_url)

def processShowName(show):
    showSynonymDict = {}
    showSynonymDict['Marvels Agents of Shield'] = "Marvel's Agents of S.H.I.E.L.D."
    showSynonymDict['Legends of Tomorrow'] = "DC's Legends of Tomorrow"
    if show in showSynonymDict:
        return showSynonymDict[show]
    else:
        return show

def getReviews(show):
    url = ("http://www.ign.com/search?page=0&count=10&filter=articles&type=article&q=review " + show).replace(" ", "%20")
    url = urllib.quote(url, safe='')
    urlRest = "https://api.import.io/store/connector/87e7f75c-3d4c-45cb-93e9-305a52237e63/_query?input=webpage/url:" + url + "&&_apikey=e581e9228fc34f139c3031d520f27af635f6dc576c932b84a8fd6cce4cc4b6a0a8499e8fcc53a7e308bf321c7a6e22998ec481eb1ab47742b062d01d62e174fc95343090d71c6dc63a4255886bf546e1"
    data = requests.get(urlRest).json()
    return data

def processDates(data):
    dateDict = {}
    for i in range(0, len(data["results"])):
        regex = re.compile('(?<=http:\/\/www.ign.com\/articles\/)(.*)(?=\/.*)', re.IGNORECASE)
        date_str = regex.findall(data["results"][i]["searchitem_link_2"])[0].split("/")
        dateDict[i] = datetime(int(date_str[0]), int(date_str[1]), int(date_str[2]))
    return dateDict

def getLatestReview(show):
    data = getReviews(show)
    dateDict = processDates(data)
    i_latest = 0
    for i in dateDict:
        if dateDict[i] > dateDict[i_latest]:
            i_latest = i
    latest = data["results"][i_latest]
    return latest


# --------------------------------------------------------------------------------------------
# 2) "I'M GOING ON A TRIP" APPLICATION

@ask.intent('TripWelcomeIntent')
def trip_welcome():
    welcome = render_template('trip_open')
    reprompt = render_template('trip_again')
    return question(welcome) \
        .reprompt(reprompt)

@ask.intent('AMAZON.CancelIntent')
@ask.intent('AMAZON.StopIntent')
@ask.intent('AMAZON.NoIntent')
def trip_nogo():
    quit = render_template('trip_nogo')
    return statement(quit)

def getCityList():
    list = ['Paris', 'London', 'Rome', 'Madrid', 'Prague', 'Venice', 'Florence', 'Dublin', 'Kopenhagen']
    return list

def getRandomElement(list):
    return random.choice(list)

def getRandomCityText(city):
    texts = ['trip_city_1', 'trip_city_2', 'trip_city_3']
    choice = getRandomElement(texts)
    cityText = render_template(choice, city=city)
    return cityText

# Hierbij vertellen dat we antwoorden met een question, omdat dit de sessie open houdt en statement niet
@ask.intent('AMAZON.YesIntent')
def trip_start():
    start = render_template('trip_start')
    cityList = getCityList()
    city = getRandomElement(cityList)
    promptedCities = [city]
    session.attributes['promptedCities'] = promptedCities
    session.attributes['currentCity'] = city
    cityPhrase = getRandomCityText(city)
    return question(start + cityPhrase)

@ask.intent('TripNextCityIntent')
def trip_nextCity():
    cityList = getCityList()
    city = getRandomElement(cityList)
    promptedCities = session.attributes['promptedCities']
    while city in promptedCities:
        # This can go into a loop if all cities have been prompted
        city = getRandomElement(cityList)
    promptedCities.append(city)
    session.attributes['promptedCities'] = promptedCities
    session.attributes['currentCity'] = city
    cityPhrase = getRandomCityText(city)
    return question(cityPhrase)

@ask.intent('TripProposeIntent')
def trip_propose(city):
    if (city is None):
        response = render_template('trip_city_propose_bad')
        return question(response)
    else:
        response = render_template('trip_city_propose_good', city=city)
        promptedCities = session.attributes['promptedCities']
        promptedCities.append(city)
        session.attributes['promptedCities'] = promptedCities
        session.attributes['currentCity'] = city
        return question(response)

@ask.intent('TripWeatherIntent')
def trip_weather():
    city = session.attributes['currentCity']
    url = 'http://api.openweathermap.org/data/2.5/weather?q=' + city
    key = '&APPID=3d02070a84a923fe26dd362ac34ce327&units=metric&lang=en'
    response = requests.get(url + key)
    descr = str(response.json()['weather'][0]['description'])
    temp = str(int(response.json()['main']['temp']))
    response = render_template('trip_weather', city=city, description=descr, temp=temp)
    return question(response)

@ask.intent('TripGoIntent')
def trip_go():
    city = session.attributes['currentCity']
    response = render_template('trip_go')
    return statement(response) \
        .simple_card(title='Your trip for ' + city, content="Don't forget to catch your plane tomorrow!")

# --------------------------------------------------------------------------------------------
# MAIN

if __name__ == '__main__':
    app.run(debug=True)