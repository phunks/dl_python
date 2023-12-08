# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import json
import shutil
import requests
import urllib.parse
import http.cookiejar
import re
import os
import time
from pathlib import Path
from bs4 import BeautifulSoup
import cookies
from cookies import make_directory


BASE_DIR = Path(__file__).resolve().parent
user_agent = "Mozilla/5.0"
get_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*",
               "Referer": "https://aaaaaa/index.jsp",
               "Cache-Control": "no-cache",
               "User-Agent": user_agent}
post_headers = {"Accept": "text/html,application/xhtml+xml,application/xml",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://aaaaaa/index.jsp",
                "User-Agent": user_agent}

proxies = {
    'http': 'http://localhost:8888',
    'https': 'http://localhost:8888',
}

download_list = []
current_dir = []
s = requests.Session()
cookie = http.cookiejar.MozillaCookieJar()

def main():
    download_target = 'xxxxxx'
    DOWNLOAD_DIR = BASE_DIR / download_target
    make_directory(DOWNLOAD_DIR)
    current_dir.append(DOWNLOAD_DIR)

    # read cookies
    cookies.get_chrome_cookies()
    arch_flg = True

    getSession()
    time.sleep(5)
    r = getBaseDirList(download_target)
    createDownloadList(r)
    for t in download_list:
        print(str(t['id']) + ", seq:" + str(t['seq']) + ", dir:" + str(t['dir']), end='\\')
        make_directory(t['dir'])
        fname = downloadFile(t['id'], t['seq'], t['dir'])
        print(fname)

    if arch_flg:
        shutil.make_archive(download_target, 'zip', download_target)

def getBaseDirList(download_target):
    _id = '70152222'
    r = \
        (_id)
    _id = getIdByNameFromDirList(r, download_target)
    r = getDirList(_id)
    _id = getIdByNameFromDirList(r, 'bbb')
    r = getDirList(_id)
    return r

def getNordInformation(_id):
    data = {"getnodeProperties": "true", "nodeId": _id}
    r = s.post('https://xxxxx/showNodeInformation.do',
               data=data, headers=post_headers,
               proxies=proxies, verify=True)
    return r

def getIdByNameFromDirList(r, name):
    _id = list(filter(lambda x: x["NAME"] == name,
                      json.loads(r.content)['data']['gridRoot']))[0]['ID']
    return _id

def createDownloadList(r):
    dlist = json.loads(r.content)['data']['gridRoot']
    for f in dlist:
        if f['NODETYPE'] == 'SHORTCUT':
            _id = f['SCT_DESTINATIONID']
            ni = getNordInformation(_id)
            nt = json.loads(ni.content)['data']['nordInformation'][0]['nodeTypeCat']
            if nt == '10': # directory
                nodeName = json.loads(ni.content)['data']['nodeInformation'][0]['nodeName']
                current_dir.append(nodeName)
                createDownloadList(getDirList(_id))
                current_dir.pop()
            elif nt == '11': #file
                seq = getFileSeq(_id)
                if seq != "":
                    download_list.append({"id": _id, "seq": seq, "dir": Path(*current_dir)})
                else:
                    print("error: append download list => " + str(_id))
        elif f['NODETYPE'] == 'FILE':
            if f['FILE_CNT'] > 1:
                print("WARNING: " + str(f['ID']) + " FILE COUNT=> " + str(f['FILE_CNT']))
            download_list.append({"id": f['ID'], "seq": f['SEQUENCE'], "dir": Path(*current_dir)})
        elif f['NODETYPE'] == 'FOLDER':
            nodeName = json.loads(getNordInformation(f['ID']).content)['data']['nodeInformation'][0]['nodeName']
            current_dir.append(nodeName)
            createDownloadList(getDirList(f['ID']))
            current_dir.pop()
        else:
            print("unknown" + str(f['ID']))

def getSession():
    COOKIES_DIR = BASE_DIR / "cookies"
    cookie_file = COOKIES_DIR / "cookie.txt"
    cookie.load(cookie_file)
    s.trust_env = False
    r = s.get('https://xxxxxx/index.jsp',
              headers=get_headers, cookies=cookie, proxies=proxies,
              verify=True, allow_redirects=False)

    while r.status_doce != 200:
        mergeCookies(r)
        if r.is_redirect:
            r = s.get(r.next.url,
                      headers=get_headers, cookies=cookie, proxies=proxies,
                      verify=True, allow_redirects=True)
        else:
            break

    bs = BeautifulSoup(r.text, features="html.parser")
    try:
        err = bs.find('div', {"id": 'errorMessage'})
        if "PCM-OIDC-" in err.text:
            print(err.text)
    except:
        pass
    if err is not None:
        raise Exception(err.text)

def mergeCookies(r):
    for c in r.cookies:
        try:
            cookie.clear(re.sub(u'.*?(\..*)', r"\1", r"\1", c.domain), c.path, c.name)
        except:
            pass
        cookie.set_cookie(
            http.Cookie(c.version, c.name, c.value, c.port, c.port_specified, c.domain, c.domain_specified,
                        c.domain_initial_dot, c.path, c.path_specified,
                        False, False, None, None, None, None))

def getDirList(_id):
    data = {"getNodeList": "true", "nodeId": _id, "start": "0",
            "limit": "100", "sort": "NAME", "dir": "ASC"}
    r = s.post('https://xxxxx/NltGetNodeList.do',
               data=data, headers=post_headers,
               proxies=proxies, vefiry=True)
    if r.status_code != 200:
        raise Exception("error: " + r.status_code)
    return r

def getFileSeq(_id):
    seq = ""
    data = {"showHistories": "true", "reload": "true", "start": "0",
            "limit": "100", "nodeId": _id, "uniqId": "20"}
    r = s.post("https://xxxxx/hisShowHistoriesJson.do",
               data=data, headers=post_headers,
               proxies=proxies, vefiry=True)
    try:
        seq = json.loads(r.content)['data']['gridRoot'][0]['SEQUENCE']
    except:
        print("devnet")
    return seq

def downloadFile(_id, seq, save_dir):
    data = {"nodeId": _id, "seq": seq}
    with s.get("https://xxxxx/cmnDownloadFile.do",
               params=data, headers=get_headers,
               proxies=proxies, vefiry=True) as r:
        if "Content-Disposition" in r.headers.keys():
            fname = urllib.parse.unquote(re.findall(".*filename.*?=utf-8\'\'(.+)",
                                                    r.headers["Content-Disposition"])[0])
            saveFilePath = os.path.join(save_dir, fname)
            with open(saveFilePath,'wb') as saveFile:
                saveFile.write(r.content)
    return fname


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

