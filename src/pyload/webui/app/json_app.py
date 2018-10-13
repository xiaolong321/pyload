# -*- coding: utf-8 -*-
from builtins import _
import os
from shutil import copyfileobj
from traceback import print_exc

from bottle import HTTPError, request, route
from pyload.utils.utils import decode, formatSize
from pyload.webui import PYLOAD
from pyload.webui.utils import login_required, apiver_check, render_to_response, toDict


def format_time(seconds):
    seconds = int(seconds)

    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return "{:02}:{:02}:{:02}".format(hours, minutes, seconds)


def get_sort_key(item):
    return item["order"]


@route(r"/json/<apiver>/status")
@route(r"/json/<apiver>/status", method="POST")
@apiver_check
@login_required("LIST")
def status():
    try:
        status = toDict(PYLOAD.statusServer())
        status["captcha"] = PYLOAD.isCaptchaWaiting()
        return status
    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/links")
@route(r"/json/<apiver>/links", method="POST")
@apiver_check
@login_required("LIST")
def links():
    try:
        links = [toDict(x) for x in PYLOAD.statusDownloads()]
        ids = []
        for link in links:
            ids.append(link["fid"])

            if link["status"] == 12:
                link["info"] = "{} @ {}/s".format(
                    link["format_eta"], formatSize(link["speed"])
                )
            elif link["status"] == 5:
                link["percent"] = 0
                link["size"] = 0
                link["bleft"] = 0
                link["info"] = _("waiting {}").format(link["format_wait"])
            else:
                link["info"] = ""

        data = {"links": links, "ids": ids}
        return data
    except Exception as e:
        print_exc()
        return HTTPError()


@route(r"/json/<apiver>/packages")
@apiver_check
@login_required("LIST")
def packages():
    print("/json/packages")
    try:
        data = PYLOAD.getQueue()

        for package in data:
            package["links"] = []
            for file in PYLOAD.get_package_files(package["id"]):
                package["links"].append(PYLOAD.get_file_info(file))

        return data

    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/package/<id:int>")
@apiver_check
@login_required("LIST")
def package(id):
    try:
        data = toDict(PYLOAD.getPackageData(id))
        data["links"] = [toDict(x) for x in data["links"]]

        for pyfile in data["links"]:
            if pyfile["status"] == 0:
                pyfile["icon"] = "status_finished.png"
            elif pyfile["status"] in (2, 3):
                pyfile["icon"] = "status_queue.png"
            elif pyfile["status"] in (9, 1):
                pyfile["icon"] = "status_offline.png"
            elif pyfile["status"] == 5:
                pyfile["icon"] = "status_waiting.png"
            elif pyfile["status"] == 8:
                pyfile["icon"] = "status_failed.png"
            elif pyfile["status"] == 4:
                pyfile["icon"] = "arrow_right.png"
            elif pyfile["status"] in (11, 13):
                pyfile["icon"] = "status_proc.png"
            else:
                pyfile["icon"] = "status_downloading.png"

        tmp = data["links"]
        tmp.sort(key=get_sort_key)
        data["links"] = tmp
        return data

    except Exception:
        print_exc()
        return HTTPError()


@route(r"/json/<apiver>/package_order/<ids>")
@apiver_check
@login_required("ADD")
def package_order(ids):
    try:
        pid, pos = ids.split("|")
        PYLOAD.orderPackage(int(pid), int(pos))
        return {"response": "success"}
    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/abort_link/<id:int>")
@apiver_check
@login_required("DELETE")
def abort_link(id):
    try:
        PYLOAD.stopDownloads([id])
        return {"response": "success"}
    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/link_order/<ids>")
@apiver_check
@login_required("ADD")
def link_order(ids):
    try:
        pid, pos = ids.split("|")
        PYLOAD.orderFile(int(pid), int(pos))
        return {"response": "success"}
    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/add_package")
@route(r"/json/<apiver>/add_package", method="POST")
@apiver_check
@login_required("ADD")
def add_package():
    name = request.forms.get("add_name", "New Package").strip()
    queue = int(request.forms["add_dest"])
    links = decode(request.forms["add_links"])
    links = links.split("\n")
    pw = request.forms.get("add_password", "").strip("\n\r")

    try:
        f = request.files["add_file"]

        if not name or name == "New Package":
            name = f.name

        fpath = os.path.join(
            PYLOAD.getConfigValue("general", "download_folder"), "tmp_" + f.filename
        )
        with open(fpath, "wb") as destination:
            copyfileobj(f.file, destination)
        links.insert(0, fpath)
    except Exception:
        pass

    name = name.decode("utf8", "ignore")
    links = list(filter(None, map(str.strip, links)))
    pack = PYLOAD.addPackage(name, links, queue)
    if pw:
        pw = pw.decode("utf8", "ignore")
        data = {"password": pw}
        PYLOAD.setPackageData(pack, data)


@route(r"/json/<apiver>/move_package/<dest:int>/<id:int>")
@apiver_check
@login_required("MODIFY")
def move_package(dest, id):
    try:
        PYLOAD.movePackage(dest, id)
        return {"response": "success"}
    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/edit_package", method="POST")
@apiver_check
@login_required("MODIFY")
def edit_package():
    try:
        id = int(request.forms.get("pack_id"))
        data = {
            "name": request.forms.get("pack_name").decode("utf8", "ignore"),
            "folder": request.forms.get("pack_folder").decode("utf8", "ignore"),
            "password": request.forms.get("pack_pws").decode("utf8", "ignore"),
        }

        PYLOAD.setPackageData(id, data)
        return {"response": "success"}

    except Exception:
        return HTTPError()


@route(r"/json/<apiver>/set_captcha")
@route(r"/json/<apiver>/set_captcha", method="POST")
@apiver_check
@login_required("ADD")
def set_captcha():
    if request.environ.get("REQUEST_METHOD", "GET") == "POST":
        try:
            PYLOAD.setCaptchaResult(
                request.forms["cap_id"], request.forms["cap_result"]
            )
        except Exception:
            pass

    task = PYLOAD.getCaptchaTask()

    if task.tid >= 0:
        return {
            "captcha": True,
            "id": task.tid,
            "params": task.data,
            "result_type": task.resultType,
        }
    else:
        return {"captcha": False}


@route(r"/json/<apiver>/load_config/<category>/<section>")
@apiver_check
@login_required("SETTINGS")
def load_config(category, section):
    conf = None
    if category == "general":
        conf = PYLOAD.getConfigDict()
    elif category == "plugin":
        conf = PYLOAD.getPluginConfigDict()

    for key, option in conf[section].items():
        if key in ("desc", "outline"):
            continue

        if ";" in option["type"]:
            option["list"] = option["type"].split(";")

        option["value"] = decode(option["value"])

    return render_to_response(
        "settings_item.html", {"skey": section, "section": conf[section]}
    )


@route(r"/json/<apiver>/save_config/<category>", method="POST")
@apiver_check
@login_required("SETTINGS")
def save_config(category):
    for key, value in request.POST.items():
        try:
            section, option = key.split("|")
        except Exception:
            continue

        if category == "general":
            category = "core"

        PYLOAD.setConfigValue(section, option, decode(value), category)


@route(r"/json/<apiver>/add_account", method="POST")
@apiver_check
@login_required("ACCOUNTS")
def add_account():
    login = request.POST["account_login"]
    password = request.POST["account_password"]
    type = request.POST["account_type"]

    PYLOAD.updateAccount(type, login, password)


@route(r"/json/<apiver>/update_accounts", method="POST")
@apiver_check
@login_required("ACCOUNTS")
def update_accounts():
    deleted = []  # dont update deleted accs or they will be created again

    for name, value in request.POST.items():
        value = value.strip()
        if not value:
            continue

        tmp, user = name.split(";")
        plugin, action = tmp.split("|")

        if (plugin, user) in deleted:
            continue

        if action == "password":
            PYLOAD.updateAccount(plugin, user, value)
        elif action == "time" and "-" in value:
            PYLOAD.updateAccount(plugin, user, options={"time": [value]})
        elif action == "limitdl" and value.isdigit():
            PYLOAD.updateAccount(plugin, user, options={"limitDL": [value]})
        elif action == "delete":
            deleted.append((plugin, user))
            PYLOAD.removeAccount(plugin, user)


@route(r"/json/<apiver>/change_password", method="POST")
@apiver_check
def change_password():

    user = request.POST["user_login"]
    oldpw = request.POST["login_current_password"]
    newpw = request.POST["login_new_password"]

    if not PYLOAD.changePassword(user, oldpw, newpw):
        print("Wrong password")
        return HTTPError()