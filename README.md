# super_cool_mawirelessusb_rp02w
Simple python script to be used with raspbery pie 0 v2w to be a wireless usb flash drive


# Why does this exist?
this is useful if you have a device that only takes stuff via usb mass storage, and having to constantly plug in an out a usb stick from that device to your pc can be annoying, with this you can keep the rooted phone plugged in the device at all times (such as for PS4/PS5 savedatas)

# Rememberer, you must turn off ftp for the files to save, do not plug it out/turn off while ftp is on

# Initial setup video
follow this video [https://youtu.be/iDgQ7o_yZgU](https://youtu.be/iDgQ7o_yZgU) up until 13:15 (you plug the raspberry pi to your device via the usb plug, not PWR IN one)
# DO NOT WATCH THE VIDEO PAST 13:15
## set your username as mawirelessusbuser to make it easier as you can just copy and paste commands, otherwise replace all instances of mawirelessusbuser with your username
# after 13:15 on the video
run the command
```
sudo truncate -s 4G /piusb.bin
```
where `4G` is your desired size, now run
```
sudo modprobe g_mass_storage file=/piusb.bin stall=0 removable=1
```
set it up normally with your device to plug into (eg PS4) and then format the usb using that device (ps4 can format it as exfat if you press options on the format as external formatted device)<br><br>
then run
```
sudo modprobe -r g_mass_storage
```
to dismount it

# python setup
run the command
```
python3 -m venv venv
```
then run
```
/home/mawirelessusbuser/venv/bin/pip install pyftpdlib
```
now you need to get the `super_cool_mawirelessusb_rp02w.py` file over here, so i would just copy that files content then do
```
nano super_cool_mawirelessusb_rp02w.py
```
right click in the window to paste, then press CRTL + S then CRTL + X, after that run
```
/home/mawirelessusbuser/venv/bin/python3 /home/mawirelessusbuser/super_cool_mawirelessusb_rp02w.py
```
itll print the http url, to that url and make sure everything is working correctly,

# run script on boot
turn off ftp, plug out the raspberry pi then plug it back in then...<br><br>
here is the service file
```
[Unit]
Description=raspberry pi acting as usb
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/mawirelessusbuser
ExecStart=/home/mawirelessusbuser/venv/bin/python3 /home/mawirelessusbuser/super_cool_mawirelessusb_rp02w.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
you want to paste that here
```
sudo nano /etc/systemd/system/super_cool_mawirelessusb_rp02w.service
```
then run these 3 commands
```
sudo systemctl daemon-reload
```
```
sudo systemctl enable super_cool_mawirelessusb_rp02w.service
```
```
sudo systemctl start super_cool_mawirelessusb_rp02w.service
```
this should now start on boot
