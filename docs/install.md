# Installing quote-box

quote-box is a small program that keeps a collection of quotes you can
browse from any device on your home network and show in a slideshow on
a wall screen. This guide walks you through setting it up on a
computer running Ubuntu — a Raspberry Pi, a mini PC, or an old laptop
all work well. Once installed, it stays running on its own; you don't
need to interact with the terminal again unless something goes wrong.

The whole thing takes about fifteen minutes if everything goes
smoothly. You will be copy-pasting commands into a terminal. You don't
need to know what any of them do beforehand — each one is explained as
we go.

## What you'll need

- A computer running Ubuntu 22.04 or newer. quote-box will live on
  this machine and run continuously. Power consumption is negligible;
  a Raspberry Pi is fine.
- About fifteen minutes.
- The ability to copy and paste a command into a terminal. We'll
  cover how to open the terminal in the next section.

## Opening a terminal

A terminal is a window where you type commands instead of clicking
buttons. It looks intimidating but it's just another app. There are
two ways to get one open, depending on how you're using your computer.

### If you're using the computer directly (monitor, keyboard)

On the Ubuntu Desktop, press **Ctrl + Alt + T**. A black window
appears. That's it.

You can also click the **Activities** corner (or press the Super key,
which is the Windows key on most keyboards), type **Terminal**, and
press Enter.

### If the computer is in another room (headless server)

If quote-box's future home is, say, a Raspberry Pi sitting in a
closet with no monitor attached, you'll use **SSH** ("secure shell")
to type commands into it from another computer.

From a Mac or another Linux machine, open a terminal there and run:

```bash
ssh username@server-ip-address
```

Replace `username` with the login name on the Pi (often `pi` or
`ubuntu`) and `server-ip-address` with the Pi's IP address on your
network (something like `192.168.1.42`). You'll be asked for the
password, then dropped into a terminal on the remote machine.

If you're connecting from a Windows machine, install
[Windows Terminal](https://aka.ms/terminal) or use the built-in
PowerShell, then run the same command.

### What the terminal looks like

Once you have one open, you'll see something like:

```
username@hostname:~$
```

The `$` at the end is the **prompt**. It means the terminal is
waiting for you to type a command and press Enter. The text in
front of it is your login name and the computer's name; you can
ignore it.

## Step 1: Check Ubuntu's version

We need Ubuntu 22.04 or newer. Type this and press Enter:

```bash
lsb_release -a
```

You should see something like:

```
Distributor ID: Ubuntu
Description:    Ubuntu 24.04.1 LTS
Release:        24.04
Codename:       noble
```

The number after `Release:` is what matters. Any value of `22.04` or
higher is good. If yours is older, [upgrade Ubuntu first](https://help.ubuntu.com/community/UpgradeNotes)
before continuing.

## Step 2: Check that Python is installed

quote-box runs on Python, which usually comes with Ubuntu. Check the
version:

```bash
python3 --version
```

You should see:

```
Python 3.10.12
```

or any version starting with `3.10` or higher. If you get a message
like `command not found`, install it:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

`sudo` ("super user do") runs the command with permission to install
system-wide programs. You'll be asked for your password the first
time you use it in a session.

## Step 3: Download quote-box

There are two ways to download the code, depending on whether you
already have a tool called **git** installed.

### Option A: With git

Most Ubuntu installs have git. Check:

```bash
git --version
```

If you see a version number, you're set. Otherwise install it:

```bash
sudo apt install git
```

Then download quote-box:

```bash
git clone https://github.com/kbennett2000/quote-box.git
cd quote-box
```

The first command copies the project into a folder called `quote-box`
in your home directory. The second command (`cd`, "change directory")
moves your terminal into that folder. Every command from here on
should be run from inside this folder.

### Option B: Without git

1. Open https://github.com/kbennett2000/quote-box in a web browser.
2. Click the green **Code** button.
3. Click **Download ZIP** at the bottom of the menu.
4. Move the downloaded `quote-box-main.zip` to your home folder.

Then back in the terminal:

```bash
sudo apt install unzip
unzip quote-box-main.zip
cd quote-box-main
```

## Step 4: Run the install script

This is the big one. The script creates a system account for the app
to run under, sets up its Python environment, installs the
dependencies, copies a default configuration file, and tells your
computer to start the app automatically every time it boots.

Run it:

```bash
sudo ./install.sh
```

(`./` means "in this folder" — that's how the terminal knows where to
find the script.)

You'll see a series of numbered steps print, each followed by a
check mark when it succeeds. After about a minute you should see a
success block like this:

```
================================================================
  quote-box is up and running.

  Open in this machine's browser:
      http://localhost:8035

  Open from another device on your LAN (try one of):
      http://192.168.1.42:8035

  Service controls:
      systemctl status quote-box
      systemctl restart quote-box
      journalctl -u quote-box -f

  Install location: /home/you/quote-box
================================================================
```

If you see an error instead, jump to
[Troubleshooting: the service won't start](troubleshooting.md#wont-start).

## Step 5: Find your server's IP address

To open quote-box from another device, you need this computer's IP
address on your home network:

```bash
hostname -I
```

You'll see something like:

```
192.168.1.42 fe80::1234:5678:9abc:def0
```

The first number — `192.168.1.42` in this example — is what you want.
The rest you can ignore. Write it down; you'll use it in the next
step. (Yours will be different from the example; the exact number
depends on your home network.)

## Step 6: Open the app in a browser

On any device on your home network — phone, tablet, laptop — open a
browser and visit:

```
http://your-ip:8035
```

Replace `your-ip` with the address you found in Step 5. For example,
if your IP was `192.168.1.42`, you'd type `http://192.168.1.42:8035`.

You should see the **profile picker** screen, asking who's reading.
Type a name and click **Create** to set up your first profile.

![Profile picker](screenshots/profile-picker.png)

From here on, the [user guide](user-guide.md) takes over.

If the page doesn't load from another device, see
[Troubleshooting: I can't reach quote-box from another device](troubleshooting.md#cant-reach).

## Step 7: Try a reboot (optional but recommended)

To confirm the app comes back automatically after a power cycle,
reboot the server:

```bash
sudo reboot
```

Wait about a minute, then refresh the browser tab on your other
device. The app should be there again.

## Changing the port

quote-box uses port `8035` by default. If something else is already
using that port, or you want to use a different one, edit
`config.json` in the project folder:

```bash
sudo nano config.json
```

`nano` is a simple text editor. Find the line:

```json
  "port": 8035,
```

Change `8035` to whatever port you want (`8085` is a common
alternative). Press **Ctrl + O** to save, then **Enter** to confirm,
then **Ctrl + X** to quit nano.

Restart the app to pick up the new port:

```bash
sudo systemctl restart quote-box
```

## Updating quote-box later

When a new version is available, update from the project folder:

```bash
cd quote-box           # or quote-box-main if you used the ZIP
sudo git pull          # or download the new ZIP and replace files
sudo ./install.sh
```

It's safe to re-run `install.sh`. The script is idempotent — it skips
anything that's already done, upgrades the Python dependencies, and
restarts the service. **Your quotes and your configuration are never
touched.**

## Stopping quote-box

To stop the app temporarily (it'll come back on the next reboot):

```bash
sudo systemctl stop quote-box
```

To start it again:

```bash
sudo systemctl start quote-box
```

To remove the app entirely — see the [admin guide](admin.md) for
the uninstall script, including a `--purge` option that also deletes
your quotes.

If something isn't working as expected, the
[troubleshooting guide](troubleshooting.md) has the common fixes.
