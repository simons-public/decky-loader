import certifi
import ssl
import uuid
import re
import subprocess

from aiohttp.web import middleware, Response
from subprocess import check_output
from time import sleep


REMOTE_DEBUGGER_UNIT = "steam-web-debug-portforward.service"

# global vars
csrf_token = str(uuid.uuid4())
ssl_ctx = ssl.create_default_context(cafile=certifi.where())
user = None
group = None

assets_regex = re.compile("^/plugins/.*/assets/.*")

def get_ssl_context():
    return ssl_ctx

def get_csrf_token():
    return csrf_token

@middleware
async def csrf_middleware(request, handler):
    if str(request.method) == "OPTIONS" or request.headers.get('Authentication') == csrf_token or str(request.rel_url) == "/auth/token" or str(request.rel_url).startswith("/plugins/load_main/") or str(request.rel_url).startswith("/static/") or str(request.rel_url).startswith("/legacy/") or str(request.rel_url).startswith("/steam_resource/") or assets_regex.match(str(request.rel_url)):
        return await handler(request)
    return Response(text='Forbidden', status='403')

# Get the user by checking for the first logged in user. As this is run
# by systemd at startup the process is likely to start before the user
# logs in, so we will wait here until they are available. Note that
# other methods such as getenv wont work as there was no $SUDO_USER to
# start the systemd service.
def set_user():
    global user
    cmd = "who | awk '{print $1}' | sort | head -1"
    while user == None:
        name = check_output(cmd, shell=True).decode().strip()
        if name not in [None, '']:
            user = name
        sleep(0.1)

# Get the global user. get_user must be called first.
def get_user() -> str:
    global user
    if user == None:
        raise ValueError("helpers.get_user method called before user variable was set. Run helpers.set_user first.")
    return user

# Set the global user group. get_user must be called first
def set_user_group() -> str:
    global group
    global user
    if user == None:
        raise ValueError("helpers.set_user_dir method called before user variable was set. Run helpers.set_user first.")
    if group == None:
        group = check_output(["id", "-g", "-n", user]).decode().strip()

# Get the group of the global user. set_user_group must be called first.
def get_user_group() -> str:
    global group
    if group == None:
        raise ValueError("helpers.get_user_group method called before group variable was set. Run helpers.set_user_group first.")
    return group

async def is_systemd_unit_active(unit_name: str) -> bool:
    res = subprocess.run(["systemctl", "is-active", unit_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0

async def stop_systemd_unit(unit_name: str) -> subprocess.CompletedProcess:
    cmd = ["systemctl", "stop", unit_name]

    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def start_systemd_unit(unit_name: str) -> subprocess.CompletedProcess:
    cmd = ["systemctl", "start", unit_name]

    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
