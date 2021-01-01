import network
import utime 
import urequests
import sys
import hmac_sha1
import machine
import neopixel
import ujson

reboot = machine.reset

SSID="-----------------------------------------"
PASSWORD="------------------------------------------"

def is_button_enabled():
  try:
    f = ujson.loads(open("psn_config.json", "r").read().replace("\n",""))
    return f["btn_enabled"]
  except OSError:
    open("psn_config.json", "w+").write(ujson.dumps({"btn_enabled":True}))
    return True
    
def enable_button():
  open("psn_config.json", "w+").write(ujson.dumps({"btn_enabled":True}))
def disable_button():
  open("psn_config.json", "w+").write(ujson.dumps({"btn_enabled":False}))

def _hmac_sha1(inp,key):
  return hmac_sha1.compute(bytes(inp, 'UTF-8'), bytes(key, 'UTF-8)'))

class API(object):
  def __init__(self, base_url, app_token):
    super(API, self).__init__()
    self.base_url = base_url
    self.app = {
      "app_id": "fr.thestaticturtle.stopnowswitch",
      "app_name": "Please Stop Now",
      "app_version": "0.0.1",
      "device_name": "uPython client"
    }
    self.app_token = app_token
    self.session_info = {}

  def login(self):
    challenge = urequests.get(self.base_url+"/login").json()["result"]["challenge"]
    self.session_info = urequests.post(self.base_url+"/login/session",json={
      "app_id": self.app["app_id"],
      "password": _hmac_sha1(self.app_token, challenge)
    }).json()
    return self.session_info["success"]
    
  def check_perm(self, perm):
    return "permissions" in self.session_info["result"] and perm in self.session_info["result"]["permissions"] and self.session_info["result"]["permissions"][perm]
  
  def parental_get_profile_id_by_name(self, name):
    profiles = urequests.get(self.base_url+"/profile",headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()["result"]
    try:
      profiles = [ p for p in profiles if p["name"] == name]
    except Exception as e:
      return -1
    if len(profiles) != 1:
      return -1
    return profiles[0]["id"]

  def parental_check_profile_denied(self, profile_name):
    profile_id = self.parental_get_profile_id_by_name(profile_name)
    data = urequests.get(self.base_url+"/network_control/"+str(profile_id),headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()
    return data["result"]["current_mode"] == "denied"

  def parental_set_profile_force_denied(self, profile_name, is_denied, toggle=False):
    profile_id = self.parental_get_profile_id_by_name(profile_name)
    data = urequests.get(self.base_url+"/network_control/"+str(profile_id),headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()["result"]
    data["override"] = (not data["override"]) if toggle else is_denied
    data["override_mode"] = "denied"
    result = urequests.put(
      self.base_url+"/network_control/"+str(profile_id),
      headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]},
      json= data
    ).json()

ANNIMATION_WIFI = "wifi"
ANNIMATION_API = "api"
ANNIMATION_ERROR = "err"
ANNIMATION_NET_ALLOWED = "na"
ANNIMATION_NET_BLOCKED = "nb"
ANNIMATION_BUTTON_EN = "en"
ANNIMATION_BUTTON_DISABLED = "dis"
class Animator(object):
  """docstring for Animator"""
  def __init__(self, neo, count):
    super(Animator, self).__init__()
    self.neo = neo
    self.count = count
    self.current_annimation = ""
    self.annimation = 50
    self.step = 1
  
  def annimation_wifi(self):
    self.annimation += self.step
    if(self.annimation > 20 or self.annimation < 2):
      self.step *= -1
    self.neo.fill( (25,25,self.annimation) )
    self.neo.write()
  
  def set_annimation(self, a):
    if(self.current_annimation != a):
      self.current_annimation = a
      if(self.current_annimation == ANNIMATION_ERROR):
        self.neo.fill( (255,0,0 ))
      elif(self.current_annimation == ANNIMATION_WIFI):
        pass
      elif(self.current_annimation == ANNIMATION_API):
        self.neo.fill( (5,0,5) )
      elif(self.current_annimation == ANNIMATION_NET_ALLOWED):
        self.neo.fill( (2,15,2) )
      elif(self.current_annimation == ANNIMATION_NET_BLOCKED):
        self.neo.fill( (15,7,0) )
      elif(self.current_annimation == ANNIMATION_BUTTON_EN):
        self.neo.fill( (5,5,5) )
      elif(self.current_annimation == ANNIMATION_BUTTON_DISABLED):
        self.neo.fill( (10,0,0) )
    
  def run(self):
    if(self.current_annimation == ANNIMATION_WIFI):
      self.annimation_wifi()
    self.neo.write()

print("Welcome to PleaseStopNow button")
print("Initialization")
np = neopixel.NeoPixel(machine.Pin(12), 10)
annims = Animator(np, 10)

sys.stdout.write("Connecting to wifi: ")
wlan=network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
wlan.connect(SSID, PASSWORD)

annims.set_annimation(ANNIMATION_WIFI)

t = utime.time()
while(wlan.ifconfig()[0]=='0.0.0.0'):
  annims.run()
  if(t + 60 < utime.time()):
    print("Failed to connect to the wifi")
    annims.set_annimation(ANNIMATION_ERROR)
    annims.run()
    sys.exit(0)
print("Connected to "+SSID+" (IP is "+str(wlan.ifconfig()[0])+")")

sys.stdout.write("Connecting to the freebox api: ")
annims.set_annimation(ANNIMATION_API)
api = API("http://192.168.1.254/api/v8","---------------------------------------------------")
if not api.login():
  annims.set_annimation(ANNIMATION_ERROR)
  annims.run()
  print("Failed login into the api")
  sys.exit(0)
print("Successfully logged inb(Session token is:"+api.session_info["result"]["session_token"]+")")

sys.stdout.write("Checking api permissions: ")
if not api.check_perm("parental"):
  annims.set_annimation(ANNIMATION_ERROR)
  annims.run()
  print("Missing parental control permission. Go into the control panel to add it. Exiting now")
  sys.exit(0)
print("All good")

pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

old_value = pin.value()
t = utime.time()
while True:
  annims.run()

  value = pin.value()
  if old_value != value:
    old_value = value
    if value == 0:
      if is_button_enabled():
        print("Button pressed, switching")
        annims.set_annimation(ANNIMATION_BUTTON_EN)
        annims.run()
        api.parental_set_profile_force_denied("test_samuel",None,toggle=True)
      else:
        print("Button pressed but not enabled")
        annims.set_annimation(ANNIMATION_BUTTON_DISABLED)
        annims.run()
        utime.sleep(0.100)
  
  if(t + 2 < utime.time()):
    sys.stdout.write("Checking status: ")
    t = utime.time()
    if(api.parental_check_profile_denied("test_samuel")):
      annims.set_annimation(ANNIMATION_NET_BLOCKED)
      print("Internet denied")
    else:
      annims.set_annimation(ANNIMATION_NET_ALLOWED)
      print("Internet allowed ")
    annims.run()
   