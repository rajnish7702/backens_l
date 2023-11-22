import time
import requests

def inspect():
    print("Called inspection")
    url2 = "http://127.0.0.1:9000/inspect/"

    payload={}
    headers = {}

    response2 = requests.request("GET", url2, headers=headers, data=payload)

    print(response2.text)

url1 = "http://127.0.0.1:9000/start_process/"

payload={}
headers = {}

response1 = requests.request("GET", url1, headers=headers, data=payload)

print(response1.text)

while True:

    url = "http://127.0.0.1:9000/trigger/"

    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)
    time.sleep(2)

    if int(response.text) == 1:
        inspect()

