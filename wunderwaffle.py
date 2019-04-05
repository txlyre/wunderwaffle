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

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger()

if os.name == "nt":
  asyncio.set_event_loop(asyncio.ProactorEventLoop())

tasks = []
slave_ids = []
tasks_list = []

async def send_data(websocket, data, my_user_id):
  log.info("id{}: send: {}".format(my_user_id, data))
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
  return price if count <= 1 else round(1.3 * calc_price(price, count - 1), 3)

def find_optimal_items(my_items, my_balance):
  temp = []
  for name in available_items:
    if my_balance > calc_price(available_items[name], my_items.count(name)):
      temp.append(calc_price(available_items[name], my_items.count(name)))
    else:
      temp.append(0)
  return temp

async def execute(code):
  proc = await asyncio.create_subprocess_shell("node -e \"var window=1;process.stdout.write(String({}))\"".format(code.replace("\"", "'")), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
  stdout, stderr = await proc.communicate()
  return stdout.decode()
  
async def spawn_worker(uri, my_user_id):
  try:
    my_balance = 0
    my_items = []
    item_to_buy = None
    item_price = 0
    async with websockets.connect(uri) as websocket:
      while True:
          log.info("active tasks {}/{}".format(len([task for task in asyncio.Task.all_tasks() if not task.done()]), len(asyncio.Task.all_tasks())))
          log.info("active workers {}/{}".format(len([task for task in tasks_list if not task.done()]), len(tasks_list)))
          time.sleep(1)
          data = await websocket.recv()
          if data[0] == "{":
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
              log.info("id{}: get: {}".format(my_user_id, data))
              if data[0] == "S":
                  data = data.split()
                  my_balance = float(data[2]) / 1000
                  log.info("id{}: balance: {}".format(my_user_id, my_balance))
                  await send_data(websocket, "C10 {} 1".format(data[3]), my_user_id)
              elif data == "BROKEN":
                  return await spawn_worker(uri, my_user_id)
              elif data == "NOT_ENOUGH_COINS":
                  continue
              elif data[0] == "M" and data[1] == "I":
                data = data.split()
                await send_data(websocket, "C10 {} 1".format(data[1]), my_user_id)
              elif data[0] == "C":
                data = " ".join(str(data).split(" ")[1:])
                data = json.loads(data)
                my_balance = float(data["score"]) / 1000
                if "items" in data:
                  my_items = data["items"]
                continue
              elif data[0] == "T" and data[1] == "R":
                 my_balance += float(str(data).split(" ")[1]) / 1000                            
                 
          if my_balance > 0 and item_to_buy:                   
            if my_balance < item_price:
              continue
            await send_data(websocket, "P{} B {}".format(random.randint(1, 20), item_to_buy), my_user_id)
            log.info("id{}: buy {} for {} coins".format(my_user_id, item_to_buy, item_price))

          some_count = random.randint(100, 1000)
          if my_balance > some_count and my_user_id != master_user_id and not random.randint(1,40)%5:
            target = random.choice(slave_ids)
            if target == my_user_id:
              continue
            await send_data(websocket, "P T {} {}".format(target, some_count), my_user_id)       
            log.info("id{}: supporting {} for {} coins".format(my_user_id, target, some_count))
           
          if my_balance > 10000 and my_user_id != master_user_id and random.randint(1,10)%2:
            count = random.randint(1000, 10000)
            await send_data(websocket, "P T {} {}".format(master_user_id, count), my_user_id)          
            log.info("id{}: send out to master {} coins".format(my_user_id, count))  
          
          optimal_items = find_optimal_items(my_items, my_balance)
          optimal_items[0] *= 1000
          optimal_items[1] = math.floor(optimal_items[1] / 3) * 1000
          optimal_items[2] *= 100;
          optimal_items[3] = math.floor(optimal_items[3] / 3) * 100
          optimal_items[4] *= 10
          optimal_items[5] *= 2
          position = optimal_items.index(min(optimal_items))

          if position == 0: 
            item_to_buy = "cursor"
          elif position == 1:
            item_to_buy = "cpu"
          elif position == 2:
            item_to_buy = "cpu_stack"
          elif position == 3:
            item_to_buy = "computer"
          elif position == 4:
            item_to_buy = "server_vk"
          elif position == 5:
            item_to_buy = "quantum_pc"
          else:
            item_to_buy = "datacenter"

          item_price = calc_price(available_items[item_to_buy], my_items.count(item_to_buy))
  except KeyboardInterrupt:
        log.info("^C catched")
        destroy_tasks()
        sys.exit(137)
  except Exception as e:
    log.error("error: {}".format(e))
    time.sleep(5)
    return await spawn_worker(uri, my_user_id)       
  log.errror("reached unreachable")
  time.sleep(5)
  return await spawn_worker(uri, my_user_id)       
            
async def dispatch_worker(token, user_id):
    url = "https://api.vk.com/method/execute.resolveScreenName?access_token={}&v=5.55&screen_name=app6915965_-176897109&owner_id=-176897109&func_v=3".format(token)
    response_json = requests.get(url).json()
    if "error" in response_json:
      log.error("failed to dispatch worker vk.com/id{}".format(user_id))
      log.error("API answer: {}".format(response_json))
      time.sleep(5)
      return await dispatch_worker(url, user_id)

    app_key = response_json["response"]["object"]["mobile_iframe_url"].split("?")[1]
     
    password = (user_id - 109) if (user_id % 2) else (user_id - 15)
    n = user_id % 16

    domain = "bagosi-go-go.vkforms.ru" if n > 7 else "coin.w5.vkforms.ru"
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
  
print("Wunderwaffle - a tiny VK Coin miner.")
print("by @txlyre, www: txlyre.website.")
print("original by vk.com/illkapaanen\n")

if not os.path.isfile("save.dat"):
  log.info("no save found, making a new one...")
  accounts = []
  master_account = ()
  with open("accs.txt", "r") as fd:
    lines = fd.readlines()
    master_account = lines.pop(0).split(":")
    master_account = (master_account[0], master_account[1].split(" ")[0])
    for line in lines:
      parts = line.split(":")
      accounts.append((parts[0], parts[1].split(" ")[0]))
  data_save = ""
  data = auth(*master_account)
  master_token, master_user_id = data["access_token"], data["user_id"]
  data_save += "{} {}\n".format(master_token, master_user_id)
  log.info("added save for master vk.com/id{}".format(master_user_id))
  for account in accounts:
    data = auth(*account)
    token, user_id = data["access_token"], data["user_id"]
    data_save += "{} {}\n".format(token, user_id)
    log.info("added save for worker vk.com/id{}".format(user_id))
  with open("save.dat", "w") as fd:
    fd.write(data_save.strip())
  
with open("save.dat", "r") as fd:
  lines = fd.readlines()
  master_account = lines.pop(0).strip().split(" ")
  master_token, master_user_id = master_account[0], int(master_account[1])
  
  tasks.append(dispatch_worker(master_token, master_user_id))
  log.info("added master vk.com/id{}".format(master_user_id))

  for line in lines:
    parts = line.strip().split(" ")
    token, user_id = parts[0], int(parts[1])
    tasks.append(dispatch_worker(token, user_id))
    slave_ids.append(user_id)
    log.info("added worker vk.com/id{}".format(user_id))

try:
  asyncio.get_event_loop().run_until_complete(run_tasks(tasks))
except KeyboardInterrupt:
  log.info("^C catched")
  destroy_tasks()
  sys.exit(137)