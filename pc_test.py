import requests
import os
import json
import sys
import time
import base64
import hashlib
import hmac

import hmac_sha1

def _hmac_sha1______(inp,key):
	print((inp,key))
	hashed = hmac.new(bytes(inp, 'UTF-8'), bytes(key, 'UTF-8'), hashlib.sha1)
	return hashed.hexdigest()

def _hmac_sha1_____(inp,key):
	print((inp,key))
	hashed = hmac.new(bytes(inp, 'UTF-8'), bytes(key, 'UTF-8'), hmac_sha1.SHA1)
	return hashed.hexdigest()

def _hmac_sha1(inp,key):
	print((inp,key))
	return hmac_sha1.compute(bytes(inp, 'UTF-8'), bytes(key, 'UTF-8)'))

# exit()

class API(object):
	"""docstring for API"""
	def __init__(self, base_url):
		super(API, self).__init__()
		self.base_url = base_url
		self.app = {
			"app_id": "fr.thestaticturtle.stopnowswitch",
			"app_name": "Please Stop Now",
			"app_version": "0.0.1",
			"device_name": "Python"
		}
		self.session_info = {}

	def _get_app_token(self ,force=False):
		if os.path.exists("token.json") and not force:
			try:
				return json.loads(open("token.json").read())["token"]
			except Exception as e:
				print(e)
				return self._get_app_token(force=True)
		else:
			response = requests.post(self.base_url+"/login/authorize",json=self.app)
			auth_start_data = json.loads(response.text)
			if not auth_start_data["success"]:
				print(auth_start_data)
				return None

			i=0
			while True:
				response = requests.get(self.base_url+"/login/authorize/"+str(auth_start_data["result"]["track_id"])).json()
				if response["success"] and response["result"]["status"] != "pending":
					break
				i+=1
				time.sleep(1)
				print("Waiting for user to grant access")
				if i>30:
					return None
			print("Auth result: "+response["result"]["status"])
			if response["result"]["status"]=="granted":
				print(auth_start_data)
				print(response)
				open("token.json","w").write(json.dumps({"token":auth_start_data["result"]["app_token"]}))
				return auth_start_data["result"]["app_token"]
			return None

	def login(self):
		app_token = self._get_app_token()
		challenge = requests.get(self.base_url+"/login").json()["result"]["challenge"]
		self.session_info = requests.post(self.base_url+"/login/session",json={
			"app_id": self.app["app_id"],
			"password": _hmac_sha1(app_token, challenge)
		}).json()
		print(self.session_info)
		return self.session_info["success"]

	def check_perm(self, perm):
		return "permissions" in self.session_info["result"] and perm in self.session_info["result"]["permissions"] and self.session_info["result"]["permissions"][perm]

	def parental_get_profile_id_by_name(self, name):
		profiles = requests.get(self.base_url+"/profile",headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()["result"]
		profiles = [ p for p in profiles if p["name"] == name]
		if len(profiles) != 1:
			return -1
		return profiles[0]["id"]

	def parental_check_profile_denied(self, profile_name):
		profile_id = self.parental_get_profile_id_by_name(profile_name)
		data = requests.get(self.base_url+"/network_control/"+str(profile_id),headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()
		print(data)
		return  data["result"]["current_mode"] == "denied"

	def parental_set_profile_force_denied(self, profile_name, is_denied):
		profile_id = self.parental_get_profile_id_by_name(profile_name)
		data = requests.get(self.base_url+"/network_control/"+str(profile_id),headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]}).json()["result"]
		data["override"] = is_denied
		data["override_mode"] = "denied"
		result = requests.put(
			self.base_url+"/network_control/"+str(profile_id),
			headers={"X-Fbx-App-Auth":self.session_info["result"]["session_token"]},
			json= data
		).json()

api = API("http://192.168.1.254/api/v8")
api.login()
if not api.check_perm("parental"):
	print("Missing parental control permission. Go into the control panel to add it. Exiting now")
	sys.exit()

# api.parental_set_profile_force_denied("test_samuel", True)
# print(api.parental_check_profile_denied("test_samuel"))

# time.sleep(5)

# api.parental_set_profile_force_denied("test_samuel", False)
# print(api.parental_check_profile_denied("test_samuel"))
