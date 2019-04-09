import asyncio
import websockets
import json
import time
import requests
import sys
import random
import os, os.path
import logging
import math
import urllib.parse
import getopt

dukpy_available = True
try:
  import dukpy
except ModuleNotFoundError:
  dukpy_available = False
  log.info("no dukpy found, using Node.js instead")

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger()

if os.name == "nt":
  asyncio.set_event_loop(asyncio.ProactorEventLoop())

verbose = False
idle_mode = False
idle_main_mode = False
no_support = False
drop_all = False
drop_amount = 10000
buy_only = None
tasks = []
slave_ids = []
tasks_list = []

async def send_data(websocket, data, my_user_id):
  if verbose:
    log.info("id{}: to: {}".format(my_user_id, data))
  await websocket.send(data)

available_items = {
  "cursor": 30,
  "cpu": 100,
  "cpu_stack": 1e3,
  "computer": 1e4,
  "server_vk": 5e4,
  "quantum_pc": 2e5,
  "datacenter": 5e6
}

def calc_price(price, count):
  return price / 1000 if count <= 1 else math.ceil(1.3 * calc_price(price, count - 1))

async def execute(code):  
  prefix = "var window={\"parseInt\": true, \"location\": {\"host\": \"iyiyiyiyi\"}, \"navigator\": { \"userAgent\": \"Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20150101 Firefox/20.0 (Chrome)\"}}"
  if dukpy_available:
    return dukpy.evaljs("{};{}".format(prefix, code))

  proc = await asyncio.create_subprocess_exec("node", "-e", "{};process.stdout.write(String({}))".format(prefix, code), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
  stdout, stderr = await proc.communicate()
  return stdout.decode()
  
async def spawn_worker(uri, my_user_id):
  if verbose:
    log.info("spawn worker vk.com/id{}".format(my_user_id))
  try:
    my_balance = 0
    my_items = []
    item_to_buy = None
    item_price = 0
    async with websockets.connect(uri) as websocket:
      while True:
          time.sleep(0.5)
          data = await websocket.recv()
          if data[0]== "{":
              data = json.loads(data)             
              if "type" in data:
                  if data["type"] == "INIT":
                      dataRandom = data["randomId"]
                      dataPow = data["pow"]
                      my_items = data["items"]
                      dataPow = await execute(dataPow)
                      await send_data(websocket, "C1 {} {}".format(dataRandom, dataPow), my_user_id)
                      await send_data(websocket, "C10 {} 1".format(dataRandom), my_user_id)
          else:
              if verbose:
                log.info("id{}: from: {}".format(my_user_id, data))
              if data[0] == "S":
                  data = data.split()
                  my_balance = float(data[2]) / 1000
                  if verbose:
                    log.info("id{}: balance: {}".format(my_user_id, my_balance))
                  await send_data(websocket, "C10 {} 1".format(data[3]), my_user_id)
              elif data[0] == "M" and data[1] == "I":
                data = data.split()
                await send_data(websocket, "C10 {} 1".format(data[1]), my_user_id)
              elif data[0] == "C":
                data = " ".join(str(data).split(" ")[1:])
                data = json.loads(data)
                my_balance = float(data["score"]) / 1000
                if "items" in data:
                  my_items = data["items"]
                  if verbose:
                    log.info("id{}: items: {}".format(",".join(my_items)))

                if verbose:
                    log.info("id{}: balance: {}".format(my_user_id, my_balance))              
              elif data[0] == "T" and data[1] == "R":
                 data = float(str(data).split(" ")[1]) / 1000 
                 my_balance += data
                 log.info("id{}: income {} coins".format(my_user_id, data))                       
              elif data[0] == "M" and data[1] == "S" and verbose:
                data = " ".join(str(data).split(" ")[1:])
                log.warning("message: {}".format(data))
                time.sleep(15)
                return await spawn_worker(uri, my_user_id)              
              elif data == "BROKEN":
                  return await spawn_worker(uri, my_user_id)
              elif data[0] == "R":
                  data = " ".join(str(data).split(" ")[1:])
                  log.warning("{}".format(data))
                  continue             
             
          if not no_support:
            some_count = random.randint(100, 1000)
            if my_balance > some_count and my_user_id != master_user_id and not random.randint(1,40)%5:
              target = random.choice(slave_ids)
              if target == my_user_id:
                continue
              await send_data(websocket, "P T {} {}".format(target, some_count * 1000), my_user_id)       
              log.info("id{}: supporting {} for {} coins".format(my_user_id, target, some_count))
              continue

          if my_balance > drop_amount and my_user_id != master_user_id and random.randint(1,10)%2:            
            count = drop_amount if drop_all else random.randint(drop_amount / 10, drop_amount)
            await send_data(websocket, "P T {} {}".format(master_user_id, count * 1000), my_user_id)          
            log.info("id{}: send out to master {} coins".format(my_user_id, count))            
            continue

          if buy_only:
            if idle_main_mode and my_user_id == master_user_id:
              continue
            item_price = calc_price(available_items[buy_only], my_items.count(buy_only))
            if verbose:
              log.info("id{}: next target is {} for cost {} coins".format(my_user_id, buy_only, item_price))

            if my_balance < item_price:
              continue
            
            log.info("id{}: buy {} for {} coins".format(my_user_id, buy_only, item_price))
            await send_data(websocket, "P{} B {}".format(random.randint(1, 20), buy_only), my_user_id)
            continue

          if not idle_mode and not buy_only:
            if idle_main_mode and my_user_id == master_user_id:
              continue
            price_a = calc_price(available_items["cursor"], my_items.count("cursor"))
            price_b = calc_price(available_items["cpu"], my_items.count("cpu"))
            price_c = calc_price(available_items["cpu_stack"], my_items.count("cpu_stack"))
            price_d = calc_price(available_items["computer"], my_items.count("computer"))
            price_e = calc_price(available_items["server_vk"], my_items.count("server_vk"))
            price_f = calc_price(available_items["quantum_pc"], my_items.count("quantum_pc"))
            price_g = calc_price(available_items["datacenter"], my_items.count("datacenter"))

            item_to_buy = "datacenter"
            if price_g / price_f >= 2:
              item_to_buy = "quantum_pc"
            if price_f / price_e >= 5:
              item_to_buy = "server_vk"
            if price_e / price_d >= 3:
              item_to_buy = "computer"
            if price_d / price_c >= 3:
              item_to_buy = "cpu_stack"
            if price_c / price_b >= 30:
              item_to_buy = "cpu"
            if price_b / price_a >= 3:
              item_to_buy = "cursor"              

            item_price = calc_price(available_items[item_to_buy], my_items.count(item_to_buy))
            if verbose:
              log.info("id{}: next target is {} for cost {} coins".format(my_user_id, item_to_buy, item_price))
            if my_balance > 0 and item_to_buy:                   
              if my_balance < item_price:
                continue
              await send_data(websocket, "P{} B {}".format(random.randint(1, 20), item_to_buy), my_user_id)
              log.info("id{}: buy {} for {} coins".format(my_user_id, item_to_buy, item_price))
              item_to_buy = None
            
  except KeyboardInterrupt:
        log.info("^C catched")
        destroy_tasks()
        sys.exit(137)
  except Exception as e:
    log.error("error: {}".format(e))
    time.sleep(10)
    return await spawn_worker(uri, my_user_id)       
  log.errror("reached unreachable")
  time.sleep(5)
  return await spawn_worker(uri, my_user_id)       
            
async def dispatch_worker(token, user_id):
    if verbose:
      log.info("dispatch worker vk.com/id{}".format(user_id))
    url = "https://api.vk.com/method/execute.resolveScreenName?access_token={}&v=5.55&screen_name=app6915965_-176897109&owner_id=-176897109&func_v=3".format(token)
    try:
      response_json = requests.get(url).json()
    except Exception as e:
      log.error("failed to dispatch worker vk.com/id{}".format(user_id))
      log.error("request failed: {}".format(e))
      time.sleep(5)
      return await dispatch_worker(url, user_id)

    if "error" in response_json:
      log.error("failed to dispatch worker vk.com/id{}".format(user_id))
      log.error("API answer: {}".format(response_json))
      time.sleep(5)
      return await dispatch_worker(url, user_id)

    app_key = response_json["response"]["object"]["mobile_iframe_url"].split("?")[1]
     
    #password = (user_id - 109) if (user_id % 2) else (user_id - 15)
    password = user_id - 1
    n = user_id % 32

    #domain = "bagosi-go-go.vkforms.ru" if n > 7 else "coin.w5.vkforms.ru"
    domain = "coin-without-bugs.vkforms.ru"
    uri = "wss://{}/channel/{}?{}&pass={}".format(domain, n, app_key, password)
    
    while True:
      try:
        await spawn_worker(uri, user_id)
      except KeyboardInterrupt:
        log.info("^C catched")
        destroy_tasks()
        sys.exit(137)
      except:
        return await dispatch_worker(uri, user_id)

def auth(login, password):
  url = "https://oauth.vk.com/token?grant_type=password&client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH&username={}&password={}".format(urllib.parse.quote(login), urllib.parse.quote(password))
  try:
    response = requests.get(url).json()
  except Exception as e:
    log.error("failed to perform request: {}".format(e))
    time.sleep(5)
    return auth(login, password)

  if "error" in response:
    log.error("failed to auth account {}@{}".format(login, password))
    log.error("API answer: {}".format(response))
    time.sleep(8)
    return auth(login, password)

  return response

def destroy_tasks():
  global tasks_list
  for task in tasks_list:
    task.cancel()
    if verbose:
      log.info("destroyed task")

async def run_tasks(task_list):
  global tasks_list
  for task in task_list:
    tasks_list.append(asyncio.get_event_loop().create_task(task))
  try:
    return await asyncio.gather(*tasks_list)
  except KeyboardInterrupt:
    log.info("^C catched")
    destroy_tasks()
    sys.exit(137)
  
print("Wunderwaffle - a tiny VK Coin miner, www: github.com/txlyre/wunderwaffle")
print("by @txlyre, www: txlyre.website\n")

if len(sys.argv) >= 2:
  try:
    opts, args = getopt.getopt(sys.argv[1:], "inmdvb:a:")
  except getopt.GetoptError as e:
    log.warning("{}".format(e))
  
  for name, value in opts:
    if name == "-i":
      idle_mode = True
      log.info("idle_mode enabled")
    elif name == "-n":
      no_support = True
      log.info("no_support enabled")
    elif name == "-m":
      idle_main_mode = True
      log.info("idle_main_mode enabled")
    elif name == "-d":
      drop_all = True
      log.info("drop_all enabled")
    elif name == "-v":
      verbose = True
      log.info("verbose enabled")
    elif name == "-b":
      if value not in available_items:
        log.warning("invalid value for '-b': {}".format(value))
        continue
      buy_only = value
      log.info("buy_only setted to {}".format(buy_only))
    elif name == "-a":
      try:
        drop_amount = int(value)
      except ValueError:
        log.warning("invalid value for '-a': {}".format(value))
        continue
      log.info("drop_amount setted to {}".format(drop_amount))
    else:
      log.warning("unknown command line argument '{}'".format(name))
    
   

if not os.path.isfile("save.dat"):
  log.info("no save found, making a new one...")
  accounts = []
  master_account = ()
  with open("accs.txt", "r") as fd:
    lines = list(filter(lambda line: not line.startswith("#"), fd.readlines()))
    master_account = lines.pop(0).strip().split(":")
    
    master_account = (master_account[0], master_account[1].split(" ")[0])
    for line in lines:
      parts = line.strip().split(":")
      accounts.append((parts[0], parts[1].split(" ")[0]))
  data_save = ""
  data = auth(*master_account)
  master_token, master_user_id = data["access_token"], data["user_id"]
  data_save += "{} {}\n".format(master_token, master_user_id)
  if verbose:
    log.info("added save for master vk.com/id{}".format(master_user_id))
  for account in accounts:
    data = auth(*account)
    token, user_id = data["access_token"], data["user_id"]
    data_save += "{} {}\n".format(token, user_id)
    if verbose:
      log.info("added save for worker vk.com/id{}".format(user_id))
  with open("save.dat", "w") as fd:
    fd.write(data_save.strip())
  
with open("save.dat", "r") as fd:
  lines = fd.readlines()
  master_account = lines.pop(0).strip().split(" ")
  if len(master_account) != 2:
    log.error("invalid master entry in save")
    sys.exit(1)
  master_token, master_user_id = master_account[0], int(master_account[1])
  
  tasks.append(dispatch_worker(master_token, master_user_id))
  if verbose:
    log.info("added master vk.com/id{}".format(master_user_id))

  for line in lines:
    parts = line.strip().split(" ")
    if len(parts) != 2:
      log.error("invalid worker entry in save")
      continue
    token, user_id = parts[0], int(parts[1])
    tasks.append(dispatch_worker(token, user_id))
    slave_ids.append(user_id)
    if verbose:
      log.info("added worker vk.com/id{}".format(user_id))

if not verbose:
  if len(slave_ids) == 0:
    log.info("account loaded")
  else:
    log.info("{} accounts loaded".format(len(slave_ids) + 1))

try:
  asyncio.get_event_loop().run_until_complete(run_tasks(tasks))
except KeyboardInterrupt:
  log.info("^C catched")
  destroy_tasks()
  sys.exit(137)