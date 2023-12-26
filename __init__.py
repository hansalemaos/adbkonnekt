import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
from functools import cache
from ctypes import wintypes
from time import sleep
from typing import Literal, Union

from subprocess_alive import is_process_alive
import psutil
from touchtouch import touch

psexe = shutil.which("powershell.exe")

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE
creationflags = subprocess.CREATE_NO_WINDOW
invisibledict = {
    "startupinfo": startupinfo,
    "creationflags": creationflags,
    "start_new_session": True,
}

windll = ctypes.LibraryLoader(ctypes.WinDLL)
kernel32 = windll.kernel32

_GetShortPathNameW = kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD


@cache
def get_short_path_name(long_name):
    try:
        output_buf_size = 4096
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        _ = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        return output_buf.value
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        return long_name


def timest():
    return time.strftime("%Y_%m_%d_%H_%M_%S")


def connect_to_all_tcp_devices_windows(
    adb_path,
    convert_to_83=False,
    adb_port=b"5037",
    sleep_after_connection_attempt=0.1,
    min_port=5550,
    no_auto_connect=(),
):
    allprocs = []
    if convert_to_83:
        adb_path = get_short_path_name(adb_path)
    netstatexe = shutil.which("netstat.exe")
    p = subprocess.run(
        [netstatexe, "-a", "-b", "-n", "-o", "-p", "TCP"],
        capture_output=True,
        **invisibledict,
    )

    for ip, port in re.findall(
        rb"^\s*TCP\s*((?:127.0.0.1)|(?:0.0.0.0)):(\d+).*LISTENING",
        p.stdout,
        flags=re.M,
    ):
        if port in [adb_port, *no_auto_connect]:
            continue
        if int(port) < min_port:
            continue
        if ip == b"0.0.0.0":
            ip = b"127.0.0.1"
        print([adb_path, "connect", ip.decode() + ":" + port.decode()])
        allprocs.append(
            subprocess.Popen(
                [adb_path, "connect", ip.decode() + ":" + port.decode()],
                **invisibledict,
            )
        )
        sleep(sleep_after_connection_attempt)

    for pr in allprocs:
        try:
            print("killing...")
            print(pr.args)
            print(pr.pid)
            pr.kill()
        except Exception:
            pass

    pde = subprocess.run(
        [adb_path, "devices", "-l"], capture_output=True, **invisibledict
    )
    fi = pde.stdout

    try:
        s1 = [
            hr[0] if hr else None
            for q in fi.strip().splitlines()
            if b"offline" in q and (hr := q.split(maxsplit=1))
        ]
        s1 = [x for x in s1 if x]
        s1 = [x.decode() for x in s1 if b"." in x and b":" in x]
        for s2 in s1:
            try:
                subprocess.run([adb_path, "disconnect", s2], **invisibledict)
            except Exception as fe:
                print(fe)
    except Exception as fe:
        sys.stderr.write(f"{fe}\n")
        sys.stderr.flush()


def run_adb_listen_to_all(
    adb_path: str,
    outputfolder: str,
    timeout_check_if_proc_running: Union[int, float] = 30,
    window_style: Literal["Hidden", "Maximized", "Minimized", "Normal"] = "Hidden",
    kill_running_adb: bool = True,
    is_alive_sleeptime: Union[int, float] = 0.1,
    check_if_alive: bool = True,
    restart_when_killed: bool = True,
    auto_connect_devices: bool = True,
    max_port_number: int = 5555,
    adb_port: int = 5037,
    adb_executables_to_kill: tuple[str] = ("hd-adb.exe", "adb.exe"),
    sleep_after_connection_attempt: Union[int, float] = 0.1,
    sleep_after_starting_the_process: Union[int, float] = 1,
    daemon: bool = False,
    priority: Literal[
        "realtime", "high", "above normal", "normal", "below normal", "low"
    ] = "above normal",
    shell: bool = True,
    listen_on_all_ports: bool = True,
    min_port: int = 5550,
    no_auto_connect: tuple[int] = (
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
    ignore_exceptions: bool = True,
    start_server_mode: bool = True,
) -> int:
    r"""
    Parameters:
    - adb_path (str): Path to the ADB executable.
    - outputfolder (str): Path to the folder where the output logs will be stored. (output only if start_server_mode is False)
    - timeout_check_if_proc_running (Union[int, float]): Timeout duration in seconds to check if the process is running.
    - window_style (Literal['Hidden', 'Maximized', 'Minimized', 'Normal']): Window style for the ADB process.
    - kill_running_adb (bool): Flag to kill any running ADB instances before starting. Default is True.
    - is_alive_sleeptime (Union[int, float]): Time in seconds to sleep while checking if the ADB process is alive.
    - check_if_alive (bool): Flag to check if the ADB process is alive. Default is True.
    - restart_when_killed (bool): Flag to restart ADB if it gets killed. Default is True.
    - auto_connect_devices (bool): Flag to automatically connect devices. Default is True.
    - max_port_number (int): Maximum port number for adb scan. Default is 5555 - ADB scans only one port, and, because
      of that, you get a great speed up .
    - adb_port (int): ADB port number. Default is 5037.
    - adb_executables_to_kill (tuple[str]): Tuple of ADB executable names to kill. Default is ("hd-adb.exe", "adb.exe").
    - sleep_after_connection_attempt (Union[int, float]): Sleep time in seconds after attempting a connection to a client.
    - sleep_after_starting_the_process (Union[int, float]): Sleep time in seconds after starting the ADB process.
    - daemon (bool): Flag to run ADB in daemon mode. Default is False. (if start_server_mode is True -> always daemon)
    - priority (Literal["realtime", "high", "above normal", "normal", "below normal", "low"]): Priority level for the
      ADB process. Default is "above normal".
    - shell (bool): Flag to use shell when starting ADB. Default is True.
    - listen_on_all_ports (bool): Flag to listen on all ports. Default is True. -> fast [re]connect
    - min_port (int): Minimum port number to consider for connections. Default is 5550.
    - no_auto_connect (tuple[int]): Tuple of port numbers to not auto-[re]connect. (HTML, SQL ...)
    - ignore_exceptions (bool): Flag to ignore exceptions and continue execution. Default is True.
    - start_server_mode (bool): Flag to start the ADB in regular mode (start-server) . Default is True.

    Returns:
    - int: Process ID of the ADB process that's running or -1 if there is no proc running


    Returns:
        from adbkonnekt import run_adb_listen_to_all
        adb_path = r"C:\Android\android-sdk\platform-tools\adb.exe"
        outputfolder=r'c:\adboutputlog'
        run_adb_listen_to_all(
            adb_path=adb_path,
            outputfolder=outputfolder,
            timeout_check_if_proc_running=30,
            window_style="Hidden",
            kill_running_adb=True,
            is_alive_sleeptime=0.05,
            check_if_alive=True,
            restart_when_killed=True,
            auto_connect_devices=True,
            max_port_number=5555,
            adb_port=5037,
            adb_executables_to_kill=("hd-adb.exe", "adb.exe"),
            sleep_after_connection_attempt=0.1,
            sleep_after_starting_the_process=1,
            daemon=False,
            priority="high",
            shell=True,
            listen_on_all_ports=True,
            min_port=5550,
            no_auto_connect=(
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
            ignore_exceptions=True,
        )

    """
    no_auto_connect = [str(x).encode() for x in no_auto_connect]
    runningpid = -1
    if restart_when_killed:
        loopvar = sys.maxsize
    else:
        loopvar = 1
    for lv in range(loopvar):
        try:
            runningpid = _run_adb_listen_to_all(
                adb_path=adb_path,
                outputfolder=outputfolder,
                WindowStyle=window_style,
                kill_running_adb=kill_running_adb,
                is_alive_sleeptime=is_alive_sleeptime,
                check_if_alive=check_if_alive,
                restart_when_killed=restart_when_killed,
                max_port_number=max_port_number,
                adb_port=adb_port,
                adb_executables_to_kill=adb_executables_to_kill,
                sleep_after_connection_attempt=sleep_after_connection_attempt,
                sleep_after_starting_the_process=sleep_after_starting_the_process,
                daemon=daemon,
                priority=priority,
                shell=shell,
                min_port=min_port,
                timeout_check_if_proc_running=timeout_check_if_proc_running,
                auto_connect_devices=auto_connect_devices,
                listen_on_all_ports=listen_on_all_ports,
                no_auto_connect=no_auto_connect,
                start_server_mode=start_server_mode,
            )
        except Exception as fe:
            if ignore_exceptions:
                sys.stderr.write(f"{fe}\n")
                sys.stderr.flush()
            else:
                raise fe

    return runningpid


def _run_adb_listen_to_all(
    adb_path,
    outputfolder,
    timeout_check_if_proc_running=30,
    WindowStyle="Hidden",
    kill_running_adb=True,
    is_alive_sleeptime=0.1,
    check_if_alive=True,
    restart_when_killed=True,
    auto_connect_devices=True,
    max_port_number=5555,
    adb_port=5037,
    adb_executables_to_kill=("hd-adb.exe", "adb.exe"),
    sleep_after_connection_attempt=0.1,
    sleep_after_starting_the_process=1,
    daemon=False,
    priority="above normal",
    shell=True,
    listen_on_all_ports=True,
    min_port=5550,
    no_auto_connect=(
        b"8080",
        b"8000",
        b"8888",
        b"1433",
        b"1521",
        b"3306",
        b"5000",
        b"5432",
        b"6379",
        b"27017",
        b"27018",
        b"8443",
        b"3389",
    ),
    start_server_mode=True,
):
    newenv = os.environ.copy()

    if max_port_number:
        subprocess.run(
            rf"""Reg.exe add "HKCU\Environment" /v "ADB_LOCAL_TRANSPORT_MAX_PORT" /t REG_SZ /d "{max_port_number}" /f""",
            shell=True,
            **invisibledict,
        )
        newenv["ADB_LOCAL_TRANSPORT_MAX_PORT"] = str(max_port_number)

    adbexename = adb_path.split(os.sep)[-1].lower()

    os.makedirs(outputfolder, exist_ok=True)
    adb_executables_to_kill = [str(x).lower() for x in adb_executables_to_kill]
    if kill_running_adb and adb_executables_to_kill:
        for p in psutil.process_iter():
            try:
                if p.name().lower() in adb_executables_to_kill:
                    print("Found instance!")
                    print(p)
                    print(p.cmdline())
                    subprocess.run(p.cmdline()[:1] + ["kill-server"], **invisibledict)

            except Exception as fe:
                pass

    FilePath = get_short_path_name(adb_path)
    if start_server_mode:
        if not listen_on_all_ports:
            cmd = f"-a -P {adb_port} start-server".split()
        else:
            cmd = f"-P {adb_port} start-server".split()
    else:
        if daemon:
            cmd = f"-a -P {adb_port} server start".split()

        else:
            cmd = f"-a -P {adb_port} nodaemon server start"

    _ArgumentList = [f"""{x.replace('"', f'{os.sep}{os.sep}"')}""" for x in cmd]
    ArgumentList = f""" -ArgumentList \\"{' '.join(_ArgumentList)}\\" """
    timestamp = timest()
    outputfile = os.path.normpath(os.path.join(outputfolder, f"{timestamp}_stdout.txt"))
    outputfileerr = os.path.normpath(
        os.path.join(outputfolder, f"{timestamp}_stderr.txt")
    )

    touch(outputfile)
    touch(outputfileerr)
    outputfile = get_short_path_name(outputfile)
    outputfileerr = get_short_path_name(outputfileerr)

    WorkingDirectory = os.sep.join(FilePath.split(os.sep)[:-1])
    wholecommandline = f"""{psexe} -ExecutionPolicy RemoteSigned Start-Process -FilePath {FilePath}{ArgumentList}-RedirectStandardOutput {outputfile} -RedirectStandardError {outputfileerr} -WorkingDirectory {WorkingDirectory} -WindowStyle {WindowStyle}"""

    subprocess.Popen(
        wholecommandline,
        cwd=WorkingDirectory,
        env=os.environ.copy(),
        shell=shell,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        **invisibledict,
    )
    adbpid = -1

    foundexe = False
    timeoutfinal = time.time() + timeout_check_if_proc_running
    psutilproc = None
    while not foundexe:
        for p in psutil.process_iter():
            if time.time() > timeoutfinal:
                break
            try:
                if p.name().lower() == adbexename:
                    if p.is_running() or is_process_alive(p.pid):
                        adbpid = p.pid
                        if "server" in p.cmdline():
                            if psutil.pid_exists(adbpid):
                                foundexe = True
                                psutilproc = p
                                break
            except Exception as fe:
                print(fe)
    sleep(sleep_after_starting_the_process)
    if priority != "normal":
        subprocess.run(
            f'wmic process where name="{adbexename}" CALL setpriority "{priority}"',
            **invisibledict,
        )
    if auto_connect_devices:
        connect_to_all_tcp_devices_windows(
            adb_path,
            convert_to_83=True,
            adb_port=str(adb_port).encode(),
            sleep_after_connection_attempt=sleep_after_connection_attempt,
            min_port=min_port,
            no_auto_connect=no_auto_connect,
        )
    if check_if_alive:
        if adbpid > 0:
            while is_process_alive(adbpid) or psutilproc.is_running():
                print(f"{adbpid} is alive", end="\r")
                sleep(is_alive_sleeptime)
    if restart_when_killed:
        if adbpid < 1 or not is_process_alive(adbpid):
            _run_adb_listen_to_all(
                adb_path=adb_path,
                outputfolder=outputfolder,
                WindowStyle=WindowStyle,
                kill_running_adb=True,
                is_alive_sleeptime=is_alive_sleeptime,
                check_if_alive=check_if_alive,
                restart_when_killed=restart_when_killed,
                max_port_number=0,
                adb_port=adb_port,
                adb_executables_to_kill=adb_executables_to_kill,
                sleep_after_connection_attempt=sleep_after_connection_attempt,
                sleep_after_starting_the_process=sleep_after_starting_the_process,
                daemon=daemon,
                priority=priority,
                shell=shell,
                min_port=min_port,
                timeout_check_if_proc_running=timeout_check_if_proc_running,
                auto_connect_devices=auto_connect_devices,
                listen_on_all_ports=listen_on_all_ports,
                no_auto_connect=no_auto_connect,
                start_server_mode=start_server_mode,
            )

    return adbpid
