from pymongo import MongoClient
# import tldextract
import json
import redis
import pickle
import os
import shutil

if not os.path.exists("./docker_config.json"):
    shutil.copy2("./config.json", "./docker_config.json")

f = open('docker_config.json')
data = json.load(f)
f.close()

MONGO_SERVER_HOST = data["server_configs"]["MONGODB_HOST"]
MONGO_SERVER_PORT = data["server_configs"]["MONGODB_PORT"]
MONGO_DB = 'LIVIS'
REDIS_HOST = data["server_configs"]["REDIS_HOST"]
REDIS_PORT = data["server_configs"]["REDIS_PORT"]
KAFKA_BROKER_URL=data["server_configs"]["KAFKA_BROKER_URL"]
INSPECTION_DELAY = data["server_configs"]["INSPECTION_DELAY"]
OPERATING_SYSTEM = data["server_configs"]["OPERATING_SYSTEM"]

default_threshold = data["inference"]["DEFAULT_THRESHOLD"]

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class MongoHelper:
    client = None
    def __init__(self):
        if not self.client:
            self.client = MongoClient(host=MONGO_SERVER_HOST, port=MONGO_SERVER_PORT)
        self.db = self.client[MONGO_DB]

    def getDatabase(self):
        return self.db

    def getCollection(self, cname, create=False, codec_options=None, domain_override = None):
        
        domain = data["username"].split("@")[1].split(".")[0]

        if cname == 'permissions' or cname == 'domains' or cname == 'user_details':
                pass
        else:
            if domain:
                cname = domain + cname

        _DB = MONGO_DB
        DB = self.client[_DB]
        # if cname in MONGO_COLLECTIONS:
        #     if codec_options:
        #         return DB.get_collection(MONGO_COLLECTIONS[cname], codec_options=codec_options)
        #     return DB[MONGO_COLLECTIONS[cname]]
        # else:
        return DB[cname]

@singleton
class CacheHelper():
    def __init__(self):
        # self.redis_cache = redis.StrictRedis(host="164.52.194.78", port="8080", db=0, socket_timeout=1)
        self.redis_cache = redis.StrictRedis(host= REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=1)
        # s.REDIS_CLIENT_HOST
        print("REDIS CACHE UP!")

    def get_redis_pipeline(self):
        return self.redis_cache.pipeline()
    
    def set_json(self, dict_obj):
        try:
            k, v = list(dict_obj.items())[0]
            v = pickle.dumps(v)
            return self.redis_cache.set(k, v)
        except redis.ConnectionError:
            return None

    def get_json(self, key):
        try:
            temp = self.redis_cache.get(key)
            #print(temp)\
            if temp:
                temp= pickle.loads(temp)
            return temp
        except redis.ConnectionError:
            return None
        return None


CacheHelper().set_json({"inspection_id":None})
CacheHelper().set_json({"result":None})
CacheHelper().set_json({"callInspectionTrigger":False})
CacheHelper().set_json({"stream_present":False})
CacheHelper().set_json({"inspect":False})
CacheHelper().set_json({"isAccepted":None})
CacheHelper().set_json({"DEFAULT_THRESHOLD":default_threshold})

save_img_folder = "saved_images"
if not os.path.exists(save_img_folder):
    os.makedirs(save_img_folder)

ocr_barcode_folder = "ocr_barcode"
if not os.path.exists(ocr_barcode_folder):
    os.makedirs(ocr_barcode_folder)

inspection_count_col = MongoHelper().getCollection("inspection_count")