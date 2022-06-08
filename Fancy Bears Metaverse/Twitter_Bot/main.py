#opensea twitter sales bot
#------------v2.2(18th March 2022)---------------
#(fix: adding failsafe by storing last_sale_creation_date in the event of a 
# missing event transaction ID in API responses)

#importing dependencies->
import tweepy 
import time
import requests
from web3 import Web3
import json
from dateutil import parser
from datetime import datetime, timezone
import asyncio

#loading config.json file data->
f = open("Twitter_Bot/config.json",)
cfg = json.load(f)

#twitter api configuring-> (to move to a config.json file)
consumer_key = cfg["consumer_key"]
consumer_secret = cfg["consumer_secret"]
access_token = cfg["access_token"]
access_token_secret = cfg["access_token_secret"]

#opensea api key->
op_api_key = cfg["opensea_api_key"]

#opensea collection to monitor for sales updates->
collection_name = cfg["collection_name"]

#twitter v2 auth->
#client = tweepy.Client(
#    consumer_key=consumer_key, consumer_secret=consumer_secret,
#    access_token=access_token, access_token_secret=access_token_secret
#)

#tweepy setup->
auth = tweepy.OAuthHandler(consumer_key, consumer_secret) 
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

#loading some past asset event (sales) IDs from json->
f3 = open("Twitter_Bot/txn_sale.json",)
id_sale = json.load(f3)
f3.close()
#if empty, latest check will add latest sale event's id^ 

def load_jsons():
    #loading some past asset event (sales) IDs from json->
    f3 = open("Twitter_Bot/txn_sale.json",)
    global id_sale
    id_sale = json.load(f3)
    f3.close()
    #if empty, latest check will add latest sale event's id^

#functions->

#formats sales update to send, sends tweet
def tweet_sender_sales(listobj, collection_name):
    print('Sending tweet...')
    title = listobj['asset']['name']
    timestamp = parser.parse(listobj['created_date'])
    url = listobj['asset']['permalink']
    price = Web3.fromWei(int(listobj['total_price']), 'ether') 
    text = title + ' purchased for Ξ'+str(price)+' Ether'
    text = text + '\n\n('+str(timestamp)+' UTC)\n\n' 
    txn = listobj['transaction']['transaction_hash']
    link=listobj['asset']['permalink']
    #link=listobj['asset']['image_url']
    txn_link= 'etherscan.io/tx/'+str(txn)
    text= text + 'Txn: '+ txn_link
    text = text + '\n\n#'+collection_name+'\n'+link
    tweet = text
    api.update_status(status=(tweet))
    print(text)
    print('-------------\n')

#get_sales2 (async function to retrieve recent sales from the collection)
def get_sales2(collection_slug):
    load_jsons()
    api_key = op_api_key
    event_match_flag = 0
    i = 0
    url = ''
    headers = {'X-API-KEY': api_key}
    successful = 0
    try:
        while(event_match_flag == 0):
            if (i==0):
                url = "https://api.opensea.io/api/v1/events?collection_slug="+str(collection_slug)+"&event_type=successful"
            print(f'%t get_sales() Iteration: {i+1} | url: {url}\n')
            response = requests.request("GET", url, headers=headers)
            print(f'%t Sales data page {i+1} retrieved. Trying to extract-')
            sales = json.loads(response.text)
            key = 'asset_events'
            if key in sales.keys():
                print(f'%t Key exists- API call successful')
                list1=sales['asset_events']
                print(f'%t json data loaded')
                print(f'%t Checking for last event match in page {i+1}...')
                pos = 0
                j = 0
                new_id = 0
                url = url+f"&cursor={sales['next']}"
                print(f'%t URL updated to = {url} (cursor next page)')
                #if id_sale["last_sale_id"] is empty, forward latest event only and add that to to the json too
                if (id_sale["last_sale_id"]==""):
                    #
                    print(f'%t Empty txn_sale.json detected- Posting latest sale only...')
                    listobj = list1[0]
                    tweet_sender_sales(listobj, collection_slug)
                    latest_id = listobj["id"]
                    creat_date = list1[0]['created_date']
                    date_obj = datetime.strptime(list1[0]['created_date'],"%Y-%m-%dT%H:%M:%S.%f")
                    utc_time = date_obj.replace(tzinfo=timezone.utc)
                    unix_timestamp = utc_time.timestamp()
                    print(f'%tLatest sale creation date was: {creat_date} (unix: {unix_timestamp})')

                    print(f'%tAdding last sale ID: {latest_id} to txn_sale.json...')
                    print(f'%tAdding last sale time: {unix_timestamp} to txn_sale.json...')
                    f = open('Twitter_Bot/txn_sale.json','r')
                    json_obj = json.load(f)
                    f.close()
                    f = open('Twitter_Bot/txn_sale.json','w')
                    json_obj["last_sale_id"] = latest_id
                    json_obj["last_sale_creation_time"] = unix_timestamp
                    json.dump(json_obj, f)
                    f.close()
                    print(f'%tNew ID: {latest_id} pushed to txn_sale.json')
                    print(f'%tNew last sale time: {unix_timestamp} pushed to txn_sale.json')
                    print(f'%t---Updated---') 
                    event_match_flag=1
                    successful = 1
                else: 
                    #New last_sale_id = latest event's ID
                    latest_id = list1[0]["id"]
                    for item in list1:
                        date_obj = datetime.strptime(item['created_date'],"%Y-%m-%dT%H:%M:%S.%f")
                        utc_time = date_obj.replace(tzinfo=timezone.utc)
                        unix_timestamp = utc_time.timestamp()
                        if (unix_timestamp <= id_sale["last_sale_creation_time"]):
                            pos = j-1
                            print(f'%tReached event prior to last embed. Page {i+1}, index {j}.')
                            print(f'%tOld last_sale_id = {id_sale["last_sale_id"]} | New last_sale_id = {latest_id}')
                            event_match_flag = 1
                            break
                        if (item["id"] == id_sale["last_sale_id"]):
                            pos = j
                            print(f'%t Last event match found at page {i+1}, index {j}. item["id"] = {item["id"]} | id_sale["last_sale_id"] = {id_sale["last_sale_id"]}')
                            print(f'%t Old last_sale_id = {id_sale["last_sale_id"]} | New last_sale_id = {latest_id}')
                            event_match_flag = 1
                            break
                        if (j==len(list1)-1):
                            break
                        j+=1
                    print(f'%t j = {j} | Len(list1) = {len(list1)}')
                    print(f'%t Forwarding earlier events in page {i+1} (upto but not including index {j}) to embed_sender_sales()...')
                    for item in list1:
                        if(j<=0):
                            break
                        print(f'%t - Sending event index {j-1} on page {i+1}.')
                        listobj = list1[j-1]
                        tweet_sender_sales(listobj, collection_slug)
                        j-=1
                    print(f'%t Forwarded all\n')
                    if (event_match_flag == 1):
                        
                        creat_date = list1[0]['created_date']
                        date_obj = datetime.strptime(list1[0]['created_date'],"%Y-%m-%dT%H:%M:%S.%f")
                        utc_time = date_obj.replace(tzinfo=timezone.utc)
                        unix_timestamp = utc_time.timestamp()
                        print(f'%t Latest sale creation date was: {creat_date} (unix: {unix_timestamp})')

                        print(f'%t Adding last sale ID: {latest_id} to txn_sale.json...')
                        print(f'%t Adding last sale time: {unix_timestamp} to txn_sale.json...')
                        f = open('Twitter_Bot/txn_sale.json','r')
                        json_obj = json.load(f)
                        f.close()
                        f = open('Twitter_Bot/txn_sale.json','w')
                        json_obj["last_sale_id"] = latest_id
                        json_obj["last_sale_creation_time"] = unix_timestamp
                        json.dump(json_obj, f)
                        f.close()
                        print(f'%t New ID: {latest_id} pushed to txn_sale.json')
                        print(f'%t New last sale time: {unix_timestamp} pushed to txn_sale.json')
                        print(f'%t ---Updated---') 

                    i+=1
                    successful = 1 
            else:
                print(f'%t Key does not exist- API call unsuccessfull. Trying again next iteration')
                successful = 0
                break
        return successful
    except Exception as e:
        print('%t get_sales() exception occurred: \n')
        print(e)
        print('%t Invoking get_sales() again, retrying in 2 seconds...')
        time.sleep(2)
        get_sales2(collection_slug)

#main function->
def main():
    a = 1
    while True:
        print(f'%t Beginning twitter bot loop...')
        response = 0
        response = get_sales2(collection_name)
        if (response==1):
            now =datetime.now()
            ctime = now.strftime("%d %b, %Y | %H:%M:%S")
            print(f'%t Last twitter sales check at: {ctime}')
        time.sleep(60)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())


