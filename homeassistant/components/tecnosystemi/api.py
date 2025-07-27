"""API Client for Tecnosystemi integration."""

from __future__ import annotations

import base64
import hashlib
import json

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class Device:
    """Represents a device in the Tecnosystemi system."""

    def __init__(self, data):
        """Initialize the device with data from the API."""
        self.LVDV_Type = data.get("LVDV_Type")
        self.LVDV_Id = data.get("LVDV_Id")
        self.DevId = data.get("DevId")
        self.Serial = data.get("Serial")
        self.Name = data.get("Name")
        self.FWVer = data.get("FWVer")
        self.OperatingMode = data.get("OperatingMode")
        self.IsOff = data.get("IsOff")
        self.LastConfigUpd = data.get("LastConfigUpd")
        self.LastSyncUpd = data.get("LastSyncUpd")
        self.LastAddTimezone = data.get("LastAddTimezone")
        self.NUM_ERROR = data.get("NUM_ERROR")


class Plant:
    """Represents a plant in the Tecnosystemi system."""

    def __init__(self, data):
        """Initialize the plant with data from the API."""
        self.LVPL_Id = data.get("LVPL_Id")
        self.LVPL_Name = data.get("LVPL_Name")
        self.LVPL_USAN_Id = data.get("LVPL_USAN_Id")
        self.LVPL_Icon = data.get("LVPL_Icon")
        self.ListDevices = [Device(d) for d in data.get("ListDevices", [])]

    def getDevices(self):
        """Return the list of devices in this plant."""
        return self.ListDevices


class AESTool:
    """AES encryption/decryption utility for Tecnosystemi API."""

    def __init__(self, salt: str) -> None:
        """Initialize the AES tool with a salt."""
        # Derive 256-bit key using SHA-256
        digest = hashlib.sha256(salt.encode("utf-8")).digest()
        self.key = digest  # Already 32 bytes for AES-256
        self.iv = bytes([0] * 16)  # 16 null bytes as IV
        self.backend = default_backend()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt the plaintext using AES in CBC mode."""
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt the ciphertext using AES in CBC mode."""
        encrypted_data = base64.b64decode(ciphertext)

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

        return decrypted.decode("utf-8")


class TecnoSystemiAPI:
    """Client for interacting with the Tecnosystemi cloud API."""

    def __init__(self, device_id, username, password):
        """Initialize the API client with credentials and device ID."""
        self.salt = "ns91wr48"
        self.fix_token = "Ga5mM61KCm5Bk18lhD5J999jC2Mu0Vaf"
        self.device_id = device_id
        self.username = username
        self.password = password
        self.base_url = "https://proair.azurewebsites.net"
        self.token = None
        self.counter = 0
        self.user_id = None
        self.session = aiohttp.ClientSession()

    def getAESTool(self):
        """Return an instance of AESTool for encryption/decryption."""
        return AESTool(self.device_id[0:8] + self.salt)

    def storeToken(self, token):
        """Store the token and counter from the encrypted token."""
        splitted_token = self.getAESTool().decrypt(token).split("_")
        if len(splitted_token) == 2:
            self.token = splitted_token[0]
            self.counter = int(splitted_token[1])
        else:
            raise ValueError("Invalid token format")

    def calcToken(self):
        """Calculate the new token using the stored token and counter."""
        if self.token is None:
            return None

        self.counter += 1  # Increment the counter for each token calculation

        # Calculate the token using the stored token and counter
        return self.getAESTool().encrypt(f"{self.token}_{self.counter}")

    async def GetPlants(self):
        """Get the list of plants from the Tecnosystemi API."""
        token = self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")
        url = self.base_url + "/api/v1/GetPlants"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token}
        async with self.session.get(url, auth=auth, headers=headers) as response:
            response_data = await response.json()
            if response.status == 200 and response_data.get("ResCode") == 0:
                return [
                    Plant(x) for x in json.loads(response_data.get("ResDescr", "[]"))
                ]
            return []

    async def getDeviceState(self, device, pin):
        """Get the state of a specific device."""
        token = self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")
        url = self.base_url + f"/api/v1/GetCUState?cuSerial={device.Serial}&PIN={pin}"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token}
        async with self.session.get(url, auth=auth, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None

    async def updateDeviceState(self, device, pin, zoneid, cmd):
        """Update the state of a specific device."""
        token = self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")

        cmd["id_zona"] = zoneid
        cmd["pin"] = pin
        cmd["c"] = "upd_zona"
        if "shu_set" not in cmd:
            cmd["shu_set"] = "0"
        if "fan_set" not in cmd:
            cmd["fan_set"] = "0"
        if "is_crono" not in cmd:
            cmd["is_crono"] = 0

        data = {
            "Serial": device.Serial,
            "Pin": pin,
            "Command": json.dumps(cmd),
            "ZoneId": zoneid,
            "Name": device.Name,
        }

        url = self.base_url + "/api/v1/UpdateZonaData"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token, "Content-Type": "application/json"}
        async with self.session.post(
            url, json=data, auth=auth, headers=headers
        ) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data.get("ResCode") == 0:
                    return True
                raise RuntimeError(
                    f"Update failed with error code: {response_data.get('ResCode')}"
                )
            raise RuntimeError(
                f"Update failed with HTTP status code: {response.status}"
            )

    async def login(self):
        """Login to the Tecnosystemi API."""
        password = self.getAESTool().encrypt(self.password)

        data = {
            "DeviceId": self.device_id,
            "Platform": "fcm2",
            "Password": password,
            "TokenPush": None,
            "Username": self.username,
        }

        url = self.base_url + "/apiTS/v2/Login"
        auth = aiohttp.BasicAuth("UsrProAir", "PwdProAir")
        headers = {"Token": self.fix_token, "Content-Type": "application/json"}
        async with self.session.post(
            url, json=data, auth=auth, headers=headers
        ) as response:
            if response.status == 200:
                login_data = await response.json()
                if login_data.get("ResCode") != 0:
                    # print("Login failed with error code:", login_data.get("ResCode"))
                    raise RuntimeError(
                        f"Login failed with error code: {login_data.get('ResCode')}"
                    )
                self.user_id = login_data.get("ID")
                self.storeToken(login_data.get("Token"))
                return True
            raise RuntimeError(f"Login failed with status code: {response.status}")
