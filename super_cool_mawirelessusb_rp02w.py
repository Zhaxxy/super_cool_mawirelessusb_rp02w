import subprocess
import json
import shutil
from pathlib import Path
import os
import threading
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class FTPHost:
    def __init__(self, directory=".", host="0.0.0.0", port=2121):
        self.directory = os.path.abspath(directory)
        self.host = host
        self.port = port

        self.server = None
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            print("FTP server is already running")
            return

        os.makedirs(self.directory, exist_ok=True)

        authorizer = DummyAuthorizer()

        # Anonymous access with read/write permissions
        authorizer.add_anonymous(
            self.directory,
            perm="elradfmwMT"
        )

        handler = FTPHandler
        handler.authorizer = authorizer
        handler.masquerade_address = None


        self.server = FTPServer(
            (self.host, self.port),
            handler
        )

        # Run FTP server in background thread
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"timeout": 0.5, "blocking": True, "handle_exit": False},
            daemon=True
        )

        self.thread.start()
        print(f"FTP server started on {self.host}:{self.port}")

    def stop(self):
        if self.server:
            self.server.close_all()
            self.server = None

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

        print("FTP server stopped")

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()


NEEDED_CLI_TOOLS = (
    'blkid',
    'sfdisk',
    'losetup',
    'mount',
    'umount',
    'truncate',
    'modprobe',
)
for needed_cli_tool in NEEDED_CLI_TOOLS:
    if not shutil.which(needed_cli_tool):
        raise Exception(f'{needed_cli_tool} is needed')
del needed_cli_tool

IMG_PATH = Path('/piusb.bin')
SHARE_POINT = '/mnt/usb_share'
HTTP_SERVER_PORT = 10167
FTP_SERVER_PORT = 10267
Path(SHARE_POINT).mkdir(exist_ok=True)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    result = s.getsockname()[0]
    s.close()
    assert isinstance(result,str)
    return result


CURRENT_IP = get_local_ip()

global_is_usb_gadget_mode_on = True
global_loop_device = None
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global ftp
        global global_is_usb_gadget_mode_on
        global global_loop_device
        if self.path == '/toggleftpserver':
            global_is_usb_gadget_mode_on = not global_is_usb_gadget_mode_on
            if global_is_usb_gadget_mode_on:
                ftp.stop()
                unmount_img_for_ftp(IMG_PATH,SHARE_POINT,global_loop_device)
                enable_usb_gadget_thing(IMG_PATH)
            else:
                disable_usb_gadget_thing()
                global_loop_device = mount_img(IMG_PATH,SHARE_POINT)
                ftp.start()
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            if not global_is_usb_gadget_mode_on:
                html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ON Button</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin-top: 100px;
            background: #f4f4f4;
        }

        .button {
            display: inline-block;
            width: 300px;
            padding: 45px 20px;
            background: #28c76f;
            color: white;
            text-decoration: none;
            font-size: 32px;
            font-weight: bold;
            border: 4px solid #15964d;
            border-radius: 8px;
            box-shadow: 0 6px 0 #117a3d;
        }

        .button:hover {
            background: #20b963;
        }

        .button:active {
            transform: translateY(4px);
            box-shadow: 0 2px 0 #117a3d;
        }

        .under-text {
            margin-top: 25px;
            font-size: 20px;
            color: #333;
        }
    </style>
</head>

<body>

    <a href="toggleftpserver" class="button">
        FTP server on
    </a>

    <p class="under-text">
        listening on AAAAAAAAAAAAAAAAAAAAAAAA
    </p>

</body>
</html>
""".replace('AAAAAAAAAAAAAAAAAAAAAAAA',f'ftp://{CURRENT_IP}:{FTP_SERVER_PORT}')
            else:
                html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OFF Button</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin-top: 100px;
            background: #f4f4f4;
        }

        .button {
            display: inline-block;
            width: 300px;
            padding: 45px 20px;
            background: #e74c3c;
            color: white;
            text-decoration: none;
            font-size: 32px;
            font-weight: bold;
            border: 4px solid #b52b20;
            border-radius: 8px;
            box-shadow: 0 6px 0 #922016;
        }

        .button:hover {
            background: #d94132;
        }

        .button:active {
            transform: translateY(4px);
            box-shadow: 0 2px 0 #922016;
        }

        .under-text {
            margin-top: 25px;
            font-size: 20px;
            color: #333;
        }
    </style>
</head>

<body>

    <a href="toggleftpserver" class="button">
        ftp server is off
    </a>

    <p class="under-text">
        it should be acting as usb mass storage now
    </p>

</body>
</html>
"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            self.wfile.write(html.encode("utf-8"))

def mount_img(img: Path, share_point: str) -> str:
    Path(SHARE_POINT).mkdir(exist_ok=True)
    data = json.loads(subprocess.check_output(
        ['sfdisk', "--json", img],
        text=True,
    ))
    partition = data["partitiontable"]["partitions"][0]

    offset = partition["start"] * data["partitiontable"]["sectorsize"]
    size = partition["size"] * data["partitiontable"]["sectorsize"]

    result = subprocess.run(
        ['blkid', "-p", "-s", "TYPE", "-o", "value", "-O", str(offset), img],
        capture_output=True,
        text=True,
        check=True
    )
    fs_type = result.stdout.strip()
    result = subprocess.run(
        ['losetup', "--offset", str(offset), "--sizelimit", str(size),"--sector-size", str(data["partitiontable"]["sectorsize"]), '--find','--show',img],
        capture_output=True,
        text=True,
        
    )
    loop_device = result.stdout.strip()
    subprocess.run(
        ['mount', "-t", fs_type, "-o", 'rw', loop_device, share_point],
        capture_output=True,
        text=True,
        check=True
    )
    return loop_device


def unmount_img_for_ftp(img: Path, share_point: str, loop_device: str | None):
    result = subprocess.run(
        ['umount', share_point],
        capture_output=True,
        text=True,
        check=True
    )
    if loop_device:
        subprocess.run(
            ['losetup', '-d',loop_device],
            capture_output=True,
            text=True,
            check=True
        )


def enable_usb_gadget_thing(img: Path) -> None:
    subprocess.run(
        ['modprobe','g_mass_storage',f'file={img}','stall=0','removable=1'],
        capture_output=True,
        text=True,
        check=True
    )


def disable_usb_gadget_thing() -> None:
    subprocess.run(
            ['modprobe','-r','g_mass_storage'],
            capture_output=True,
            text=True,
            check=True
        )


def main() -> int:
    global global_is_usb_gadget_mode_on
    global global_loop_device
    global ftp
    if os.geteuid() != 0:
        print("Not running with sudo")
        return 1
    if not IMG_PATH.is_file():
        while True:
            gb_num_str = input('how many gb you want your usb?: ')
            try:
                gb_num = int(gb_num_str.strip())
            except Exception:
                print('please enter a number')
                continue
            break
        print('\n\n' + '#'*120 + '\n\n')
        print(f'run the command \nsudo truncate -s 4G {IMG_PATH.as_posix()}\nthen run the command\nsudo modprobe g_mass_storage file=/piusb.bin stall=0 removable=1\nformat the usb using the host device, then run\nsudo modprobe -r g_mass_storage\nthen run this script again')        
        return 1
    disable_usb_gadget_thing()
    print('checking if can mount img')
    unmount_img_for_ftp(IMG_PATH,SHARE_POINT,mount_img(IMG_PATH,SHARE_POINT))
    global ftp
    ftp = FTPHost(
        directory=SHARE_POINT,
        host=CURRENT_IP,
        port=FTP_SERVER_PORT
    )
    ftp.start()
    if global_is_usb_gadget_mode_on:
        ftp.stop()
        enable_usb_gadget_thing(IMG_PATH)
    else:
        disable_usb_gadget_thing()
        global_loop_device = mount_img(IMG_PATH,SHARE_POINT)
        ftp.start()
    server = HTTPServer((CURRENT_IP, HTTP_SERVER_PORT), SimpleHandler)
    print(F'http server on http://{CURRENT_IP}:{HTTP_SERVER_PORT}')
    server.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
