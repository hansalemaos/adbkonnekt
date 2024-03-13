# automates ADB management in Windows, ensuring ADB listens to all TCP (no USB!) devices, handles configurations, and restarts if killed

## pip install adbkonnekt 

### Tested against Windows / Python 3.11 / Anaconda / BlueStacks / LdPlayer / MeMu 


#### ADB 

https://developer.android.com/tools/releases/platform-tools

```python
from konfigleser import write_config_file
import sys
import subprocess

# Use a config file:
r"""
[DEFAULT]
outputfolder = C:\stdoutstderradblog
adb_path = C:\ProgramData\chocolatey\lib\adb\tools\platform-tools\adb.exe
shell = False
window_style = Maximized
timeout_check_if_proc_running = 30
kill_running_adb = True
is_alive_sleeptime = 0.05
check_if_alive = True
restart_when_killed = True
auto_connect_devices = True
max_port_number = 5555
adb_port = 5037
adb_executables_to_kill = ('hd-adb.exe', 'adb.exe')
sleep_after_connection_attempt = 0.1
sleep_after_starting_the_process = 1
daemon = False
priority = high
listen_on_all_ports = True
min_port = 5550
no_auto_connect = (8080, 8000, 8888, 1433, 1521, 3306, 5000, 5432, 6379, 27017, 27018, 8443, 3389)
ignore_exceptions = True
new_connection_interval = 30
update_shared_devices_info = 30
"""

# Parameters:
# - adb_path (str): Path to the ADB executable.
# - outputfolder (str): Path to the folder where the output logs will be stored.
# - timeout_check_if_proc_running (Union[int, float]): Timeout duration in seconds to check if the process is running.
# - window_style (Literal['Hidden', 'Maximized', 'Minimized', 'Normal']): Window style for the ADB process.
# - kill_running_adb (bool): Flag to kill any running ADB instances before starting. Default is True.
# - is_alive_sleeptime (Union[int, float]): Time in seconds to sleep while checking if the ADB process is alive.
# - check_if_alive (bool): Flag to check if the ADB process is alive. Default is True.
# - restart_when_killed (bool): Flag to restart ADB if it gets killed. Default is True.
# - auto_connect_devices (bool): Flag to automatically connect devices. Default is True.
# - max_port_number (int): Maximum port number for adb scan. Default is 5555 - ADB scans only one port, and, because
#   of that, you get a great speed up .
# - adb_port (int): ADB port number. Default is 5037.
# - adb_executables_to_kill (tuple[str]): Tuple of ADB executable names to kill. Default is ("hd-adb.exe", "adb.exe").
# - sleep_after_connection_attempt (Union[int, float]): Sleep time in seconds after attempting a connection to a client.
# - sleep_after_starting_the_process (Union[int, float]): Sleep time in seconds after starting the ADB process.
# - daemon (bool): Flag to run ADB in daemon mode. Default is False. (if start_server_mode is True -> always daemon)
# - priority (Literal["realtime", "high", "above normal", "normal", "below normal", "low"]): Priority level for the
#   ADB process. Default is "above normal".
# - shell (bool): Flag to use shell when starting ADB. Default is True.
# - listen_on_all_ports (bool): Flag to listen on all ports. Default is True. -> fast [re]connect
# - min_port (int): Minimum port number to consider for connections. Default is 5550.
# - no_auto_connect (tuple[int]): Tuple of port numbers to not auto-[re]connect. (HTML, SQL ...)
# - ignore_exceptions (bool): Flag to ignore exceptions and continue execution. Default is True.
# - new_connection_interval (Union[int, float]): Time in seconds to wait between checking new connections. Default is 30. / 0 disables it
# - update_shared_devices_info (Union[int, float]): Time in seconds to update the shared memory dict to get the devices information.


# or a dict and convert it to a config file
adbexe = r"C:\ProgramData\chocolatey\lib\adb\tools\platform-tools\adb.exe"
cfgdata = {
    "DEFAULT": {
        "outputfolder": "C:\\stdoutstderradblog",
        "adb_path": adbexe,
        "shell": False,
        "window_style": "Maximized",
        "timeout_check_if_proc_running": 30,
        "kill_running_adb": True,
        "is_alive_sleeptime": 0.05,
        "check_if_alive": True,
        "restart_when_killed": True,
        "auto_connect_devices": True,
        "max_port_number": 5555,
        "adb_port": 5037,
        "adb_executables_to_kill": ("hd-adb.exe", "adb.exe"),
        "sleep_after_connection_attempt": 0.1,
        "sleep_after_starting_the_process": 1,
        "daemon": False,
        "priority": "high",
        "listen_on_all_ports": True,
        "min_port": 5550,
        "no_auto_connect": (
            8080,
            8000,
            8888,
            1433,
            1521,
            3306,
            5000,
            5432,
            6379,
            27017,
            27018,
            8443,
            3389,
        ),
        "ignore_exceptions": True,
        "new_connection_interval": 30,
        "update_shared_devices_info": 30,
    }
}
savepath = "c:\\adb_connection_config.ini"
write_config_file(d=cfgdata, filepath=savepath)

# run the init_file in a subprocess, it creates a completely detached process with powershell (needs elevated/admin rights!!),
# that means you can close this python script here after you see the other console running
p = subprocess.Popen(
    [
        sys.executable,
        r"C:\ProgramData\anaconda3\envs\a0\Lib\site-packages\adbkonnekt\__init__.py",  # path is different on your pc
        savepath,
    ],
)
print(p)

# After running the script, you can have access to all device information by using

# from sharedbuiltinmutables import MemSharedDict
# emulatordata = MemSharedDict({}, name="ADBDEVICES", size=4096000)
# print(emulatordata)

# You don't have to be in the same env, even different versions of Python will work.

```