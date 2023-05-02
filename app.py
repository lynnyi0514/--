from __future__ import unicode_literals
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage, ButtonsTemplate, TemplateSendMessage, URITemplateAction
import json
import configparser
import os
import string
import random
import requests
import googlemaps
from random import sample

# import pandas as pd
# import apiai
from urllib import parse
app = Flask(__name__, static_url_path='/static')
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])
GOOGLE_API_KEY = 'AIzaSyCh99R3Y1hnPZ-oP2dxqrnfZgGiZuRuVf0'
# GOOGLE_API_KEY = os.environ.get('AIzaSyCh99R3Y1hnPZ-oP2dxqrnfZgGiZuRuVf0')
# DIALOGFLOW_CLIENT_ACCESS_TOKEN = os.environ.get(
#     'DIALOGFLOW_CLIENT_ACCESS_TOKEN')
# ai = apiai.ApiAI(DIALOGFLOW_CLIENT_ACCESS_TOKEN)

config = configparser.ConfigParser()
config.read('config.ini')

line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))
my_line_id = config.get('line-bot', 'my_line_id')
end_point = config.get('line-bot', 'end_point')
line_login_id = config.get('line-bot', 'line_login_id')
line_login_secret = config.get('line-bot', 'line_login_secret')
my_phone = config.get('line-bot', 'my_phone')
HEADER = {
    'Content-type': 'application/json',
    'Authorization': F'Bearer {config.get("line-bot", "channel_access_token")}'
}


@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return 'ok'
    body = request.json
    events = body["events"]
    if request.method == 'POST' and len(events) == 0:
        return 'ok'
    print(body)
    if "replyToken" in events[0]:
        payload = dict()
        replyToken = events[0]["replyToken"]
        payload["replyToken"] = replyToken
        if events[0]["type"] == "message":
            if events[0]["message"]["type"] == "text":
                text = events[0]["message"]["text"]

                if text == "我的名字":
                    payload["messages"] = [getNameEmojiMessage()]
                elif text == "要吃什麼?":
                    payload["messages"] = [getUserIntentMessage]
                elif text == "出去玩囉":
                    payload["messages"] = [getPlayStickerMessage()]
                elif text == "台北101":
                    payload["messages"] = [getTaipei101ImageMessage(),
                                           getTaipei101LocationMessage(),
                                           getMRTVideoMessage()]
                elif text == "quoda":
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": getTotalSentMessageCount()
                        }
                    ]
                elif text == "今日確診人數":
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": getTodayCovid19Message()
                        }
                    ]

                elif text == "主選單":
                    payload["messages"] = [
                        {
                            "type": "template",
                            "altText": "This is a buttons template",
                            "template": {
                                    "type": "buttons",
                                    "title": "Menu",
                                    "text": "Please select",
                                    "actions": [
                                        {
                                            "type": "message",
                                            "label": "我的名字",
                                            "text": "我的名字"
                                        },
                                        {
                                            "type": "message",
                                            "label": "今日確診人數",
                                            "text": "今日確診人數"
                                        },
                                        {
                                            "type": "uri",
                                            "label": "聯絡我",
                                            "uri": f"tel:{my_phone}"
                                        }
                                    ]
                            }
                        }
                    ]
                else:
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                replyMessage(payload)

            elif events[0]["message"]["type"] == "location":
                # print(events)
                # title = events[0]["message"]["title"]
                # latitude = events.message.latitude
                # longitude = events.message.longitude
                latitude = events[0]["message"]["latitude"]
                longitude = events[0]["message"]["longitude"]
                payload["messages"] = [Restaurant(latitude, longitude)]
                replyMessage(payload)
        elif events[0]["type"] == "postback":
            if "params" in events[0]["postback"]:
                reservedTime = events[0]["postback"]["params"]["datetime"].replace(
                    "T", " ")
                payload["messages"] = [
                    {
                        "type": "text",
                        "text": F"已完成預約於{reservedTime}的叫車服務"
                    }
                ]
                replyMessage(payload)
            else:
                data = json.loads(events[0]["postback"]["data"])
                action = data["action"]
                if action == "get_near":
                    data["action"] = "get_detail"
                    payload["messages"] = [getCarouselMessage(data)]
                elif action == "get_detail":
                    del data["action"]
                    payload["messages"] = [getTaipei101ImageMessage(),
                                           getTaipei101LocationMessage(),
                                           getMRTVideoMessage(),
                                           getCallCarMessage(data)]
                replyMessage(payload)

    return 'OK'


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def pretty_echo(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )


@app.route("/sendTextMessageToMe", methods=['POST'])
def sendTextMessageToMe():
    pushMessage({})
    return 'OK'


def Restaurant(latitude, longitude):
    # 獲取使用者的經緯度

    # 使用 Google API Start =========
    # 1. 搜尋附近餐廳
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?key={}&location={},{}&rankby=distance&type=restaurant&fields=name,business_status,vicinity,opening_hours&language=zh-TW".format(
        GOOGLE_API_KEY, latitude, longitude)
    # nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?key={}&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(
    #     GOOGLE_API_KEY, latitude, longitude)

    nearby_results = requests.get(nearby_url)
    # print(nearby_url)
    # print(f"result : {nearby_results.text}")

    # 2. 得到最近的20間餐廳
    nearby_restaurants_dict = nearby_results.json()
    top20_restaurants = nearby_restaurants_dict["results"]
    # print(f"result : {top20_restaurants}")

    # CUSTOMe choose rate >= 4
    res_num = (len(top20_restaurants))  # 20
    above4 = []
    restaurant = []
    for i in range(res_num):
        try:
            if (top20_restaurants[i]['rating'] > 3.9) and (top20_restaurants[i]['business_status'] == 'OPERATIONAL'):
                print('rate: ', top20_restaurants[i]['rating'])
                above4.append(i)
                restaurant.append(top20_restaurants[i])
        except KeyError:
            pass

    if len(above4) == 0:
        print('附近沒有4星以上餐廳')
    # print(above4)
    # print(f"restaurant :{restaurant}")
    # 3. 隨機選擇一間餐廳

    restaurant5 = random.sample(restaurant, 3)

    # print(f"restaurant5 :{restaurant5}")

    # print(len(restaurant5))
    # 4. 檢查餐廳有沒有照片，有的話會顯示
    map_url = []
    thumbnail_image_url = []
    details = []
    phone_number = []
    # details_restaurants = []
    for i in range(len(restaurant5)):
        if restaurant5[i]["photos"] is None:
            thumbnail_image_url[i] = None
        else:
            #     # 根據文件，最多只會有一張照片
            photo_reference = restaurant5[i]["photos"][0]["photo_reference"]
            thumbnail_image_url.append("https://maps.googleapis.com/maps/api/place/photo?key={}&photoreference={}&maxwidth=1024".format(
                GOOGLE_API_KEY, photo_reference))
        # print(thumbnail_image_url)
        # 5. 組裝餐廳詳細資訊

        details_url = "https://maps.googleapis.com/maps/api/place/details/json?key={}&placeid={place_id}&language=zh-TW".format(
            GOOGLE_API_KEY, place_id=restaurant5[i]["place_id"])
        details_results = requests.get(details_url)
        details_dict = details_results.json()
        # details_restaurants = details_dict["result"]
        phone_number.append(details_dict["result"]["formatted_phone_number"].replace(
            " ", ""))

        # print(details_restaurants)
        # print(phone_number)

        if restaurant5[i]["rating"] is None:
            rating = "無"
        else:
            rating = restaurant5[i]["rating"]
        # if details_restaurants[i]["address_components"]["formatted_address"] is None:
        #     address = "沒有資料"
        # else:
        #     address = details_restaurants[i]["address_components"]["formatted_address"]
        if restaurant5[i]["vicinity"] is None:
            address = "沒有資料"
        else:
            address = restaurant5[i]["vicinity"]

        if restaurant5[i]["opening_hours"]["open_now"] == True:
            openhours = "營業中"
        else:
            openhours = "休息中"

        details.append("評分：{}星\n地址：{}\n營業狀態:{}".format(
            rating, address,  openhours))

    # 6. 取得餐廳的 Google map 網址

        map_url.append("https://www.google.com/maps/search/?api=1&query={lat},{long}&query_place_id={place_id}".format(
            lat=restaurant5[i]["geometry"]["location"]["lat"],
            long=restaurant5[i]["geometry"]["location"]["lng"],
            place_id=restaurant5[i]["place_id"]
        ))
    # print(map_url)

    ############ 整理資料##########

    message = {
        "type": "template",
        "altText": "this is a carousel template",
        "template": {
            "type": "carousel",
            "imageAspectRatio": "rectangle",
            "imageSize": "cover",
            "columns": [
                {
                    "thumbnailImageUrl": thumbnail_image_url[0],
                    "imageBackgroundColor": "#FFFFFF",
                    "title": restaurant5[0]['name'][:40],
                    "text": details[0],
                    "actions": [
                        {
                            "type": "uri",
                            "label": "查看地圖",
                            "uri":  map_url[0]
                        },
                        {
                            "type": "uri",
                            "label": "撥打電話",
                            "uri": "tel:{}".format(phone_number[0])
                        }

                    ]
                },
                {
                    "thumbnailImageUrl": thumbnail_image_url[1],
                    "imageBackgroundColor": "#FFFFFF",
                    "title": restaurant5[1]['name'][:40],
                    "text": details[1],
                    "actions": [
                        {
                            "type": "uri",
                            "label": "查看地圖",
                            "uri":  map_url[1]
                        },
                        {
                            "type": "uri",
                            "label": "撥打電話",
                            "uri": "tel:{}".format(phone_number[1])
                        }
                    ]
                },
                {
                    "thumbnailImageUrl": thumbnail_image_url[2],
                    "imageBackgroundColor": "#FFFFFF",
                    "title": restaurant5[2]['name'][:40],
                    "text": details[2],
                    "actions": [
                        {
                            "type": "uri",
                            "label": "查看地圖",
                            "uri":  map_url[2]
                        },
                        {
                            "type": "uri",
                            "label": "撥打電話",
                            "uri": "tel:{}".format(phone_number[2])
                        }
                    ]
                }

            ]

        }
    }
    return message


def getNameEmojiMessage():
    lookUpStr = string.ascii_uppercase + string.ascii_lowercase
    productId = "5ac21b4f031a6752fb806d59"
    name = "Lynn"
    message = dict()
    message['type'] = "text"
    message['text'] = "$" * len(name)
    emojis = list()
    for i, c in enumerate(name):
        emojis.append({
            "index": i,
            "productId": productId,
            "emojiId": f"{lookUpStr.index(c) + 1}".zfill(3)
        })
    message['emojis'] = emojis
    print(message)
    return message


def getUserIntentMessage():
    message = {
        "type": "template",
        "altText": "請告訴我你的位置~",
        "template": {
            "type": "buttons",
            "text": "請告訴我你的位置~",
            "actions": [
                {
                    "type": "URITemplateAction",
                    "label": "傳送我的位置",
                    "uri": "line://nv/location"

                }

            ]
        }
    }
    return message


def getCarouselMessage(data):
    message = {
        "type": "template",
        "altText": "this is a image carousel template",
        "template": {
            "type": "image_carousel",
            "columns": [
                {
                    "imageUrl": F"{end_point}/static/taipei_101.jpeg",
                    "action": {
                        "type": "postback",
                        "label": "台北101",
                        "data": json.dumps(data)
                    }
                },
                {
                    "imageUrl": F"{end_point}/static/taipei_1.jpeg",
                    "action": {
                        "type": "postback",
                        "label": "台北101",
                        "data": json.dumps(data)
                    }
                },
                {
                    "imageUrl": F"{end_point}/static/place_1.jpg",
                    "action": {
                        "type": "postback",
                        "label": "松菸文創園區",
                        "data": json.dumps(data)
                    }
                },
                {
                    "imageUrl": F"{end_point}/static/place_1.jpg",
                    "action": {
                        "type": "postback",
                        "label": "更多資訊",
                        "text": "更多資訊"
                    }
                }

            ]
        }
    }
    return message


def getCallCarMessage(data):
    message = {
        "type": "template",
        "altText": "this is a template",
        "template": {
            "type": "buttons",
            "text": f"請選擇至 {data['title']} 預約叫車時間",
            "actions": [
                {
                    "type": "datetimepicker",
                    "label": "預約",
                    "data": json.dumps(data),
                    "mode": "datetime",
                }

            ]
        }
    }
    return message


# def getLocationConfirmMessage(title, latitude, longitude):
#     data = {"latitude": latitude, "longitude": longitude,
#             "title": title, "action": "get_near"}
#     message = {
#         "type": "template",
#         "altText": "this is a buttons template",
#         "template": {
#             "type": "buttons",
#             "text": f"是否要搜尋 {title} 附近的餐廳?",
#             "actions": [
#                 {
#                     "type": "postback",
#                     "label": "是",
#                     "data": json.dumps(data),
#                     "displayText": "是",
#                 },
#                 {
#                     "type": "message",
#                     "label": "否",
#                     "text": "否"
#                 }
#             ]
#         }
#     }
#     return message


def getPlayStickerMessage():
    message = {
        "type": "sticker",
        "packageId": "789",
        "stickerId": "10856"
    }
    return message


def getTaipei101LocationMessage():
    message = {
        "type": "location",
        "title": "台北101",
        "address": "110台北市信義區市府路45號",
        "latitude": 25.0341222,
        "longitude": 121.5611909
    }
    return message


def getMRTVideoMessage():
    message = {
        "type": "video",
        "originalContentUrl": F"{end_point}/static/taipei_101_video.mp4",
        "previewImageUrl": F"{end_point}/static/taipei_101.jpeg"
    }
    return message


def getMRTSoundMessage():
    message = dict()
    message["type"] = "audio"
    message["originalContentUrl"] = F"{end_point}/static/mrt_sound.m4a"
    import audioread
    with audioread.audio_open('static/mrt_sound.m4a') as f:
        # totalsec contains the length in float
        totalsec = f.duration
    message["duration"] = totalsec * 1000
    return message


def getTaipei101ImageMessage(originalContentUrl=F"{end_point}/static/taipei_101.jpeg"):
    return getImageMessage(originalContentUrl)


def getImageMessage(originalContentUrl):
    message = {
        "type": "image",
        "originalContentUrl": originalContentUrl,
        "previewImageUrl": originalContentUrl
    }
    return message


def replyMessage(payload):
    response = requests.post(
        "https://api.line.me/v2/bot/message/reply", headers=HEADER, json=payload)
    print(response.text)
    return 'OK'


def pushMessage(payload):
    response = requests.post(
        "https://api.line.me/v2/bot/message/push", headers=HEADER, json=payload)
    print(response.text)
    return 'OK'


def getTotalSentMessageCount():
    response = requests.get(
        "https://api.line.me/v2/bot/message/quota/consumption", headers=HEADER)
    totalUsage = response.json()['totalUsage']
    return totalUsage


def getTodayCovid19Message():
    response = requests.get(
        "https://covid-19.nchc.org.tw/api/covid19?CK=covid-19@nchc.org.tw&querydata=3001&limited=TWN")
    data = response.json()[0]
    date = data['a04']
    total_count = data['a05']
    count = data['a06']
    return F"日期：{date}, 人數：{count}, 確診總人數：{total_count}"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@ app.route('/upload_file', methods=['POST'])
def upload_file():
    payload = dict()
    if request.method == 'POST':
        file = request.files['file']
        print("json:", request.json)
        form = request.form
        age = form['age']
        gender = ("男" if form['gender'] == "M" else "女") + "性"
        if file:
            filename = file.filename
            img_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(img_path)
            print(img_path)
            payload["to"] = my_line_id
            payload["messages"] = [getImageMessage(F"{end_point}/{img_path}"),
                                   {
                "type": "text",
                "text": F"年紀：{age}\n性別：{gender}"
            }
            ]
            pushMessage(payload)
    return 'OK'


@ app.route('/line_login', methods=['GET'])
def line_login():
    if request.method == 'GET':
        code = request.args.get("code", None)
        state = request.args.get("state", None)

        if code and state:
            HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
            url = "https://api.line.me/oauth2/v2.1/token"
            FormData = {"grant_type": 'authorization_code', "code": code, "redirect_uri": F"{end_point}/line_login",
                        "client_id": line_login_id, "client_secret": line_login_secret}
            data = parse.urlencode(FormData)
            content = requests.post(url=url, headers=HEADERS, data=data).text
            content = json.loads(content)
            url = "https://api.line.me/v2/profile"
            HEADERS = {
                'Authorization': content["token_type"]+" "+content["access_token"]}
            content = requests.get(url=url, headers=HEADERS).text
            content = json.loads(content)
            name = content["displayName"]
            userID = content["userId"]
            pictureURL = content["pictureUrl"]
            statusMessage = content.get("statusMessage", "No status message")
            print(content)
            return render_template('profile.html', name=name, pictureURL=pictureURL, userID=userID, statusMessage=statusMessage)
        else:
            return render_template('login.html', client_id=line_login_id,
                                   end_point=end_point)


if __name__ == "__main__":
    app.debug = True
    app.run()
