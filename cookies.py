import sqlite3
from pathlib import Path
from typing import Tuple


def get_chrome_cookies(db=None):
    import json
    import pandas as pd
    from base64 import b64decode
    from Cryptodome.Cipher.AES import new, MODE_GCM

    if db is None:
        from os.path import expandvars
        db = expandvars('%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Network\\Cookies')
        kf = expandvars('%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Local State')

        with open(kf) as f:
            keydpapi = b64decode(json.load(f)['os_crypt']['encrypted_key'].encode('utf-8'))[5:]
            key = CryptUnprotectData(keydpapi)

    conn = sqlite3.connect(db)
    conn.create_function('decrypt', 1, lambda v: new(key, MODE_GCM, v[3:15]).decrypt(v[15:-16]).decode())
    df = pd.read_sql_query("""\
        SELECT host_key, is_httponly, path, is_secure,
         expires_utc,name, decrypt(encrypted_value) as value
         FROM cookies where host_key like '%'""", conn)
    conn.close()

    BASE_DIR = Path(__file__).resolve().parent
    COOKIES_DIR = BASE_DIR / "cookies"
    _, cookies_dir = make_directory(COOKIES_DIR)
    output_file = COOKIES_DIR / "cookie.txt"
    formatted_cookies = ["# Netscape HTTP Cookie File", ]

    for row in df.itertuples(index=False):
        formatted_cookies.append(
            "\t".join([to_domain(row.host_key), "TRUE", row.path,
                       to_boolean(row.is_secure), str(epoch_from_webkit(row.expires_utc)),
                       row.name, row.value]))

    output_file.write_text("\n".join(formatted_cookies))


def make_directory(_dir: Path) -> Tuple[bool, Path]:
    created = False
    if not _dir.exists():
        try:
            _dir.mkdir(parents=True)
            created = True
        except FileExistsError:
            pass
        else:
            print(f"[Created]: {_dir.name} directory.")
    return created, _dir


def CryptUnprotectData(cipher_text=b'', entropy=b'', reserved=None, prompt_struct=None):
    import ctypes
    import ctypes.wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ('cbData', ctypes.wintypes.DWORD),
            ('pbData', ctypes.POINTER(ctypes.c_char))
        ]

    blob_in, blob_entropy, blob_out = map(
        lambda x: DataBlob(len(x), ctypes.create_string_buffer(x)),
        [cipher_text, entropy, b'']
    )
    desc = ctypes.c_wchar_p()

    CRYPTPROTECT_UI_FORBIDDEN = 0x01

    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), ctypes.byref(
                desc), ctypes.byref(blob_entropy),
            reserved, prompt_struct, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(
                blob_out)
    ):
        raise RuntimeError('Failed to decrypt the cipher text with DPAPI')
    buffer_out = ctypes.create_string_buffer(int(blob_out.cbData))
    ctypes.memmove(buffer_out, blob_out.pbData, blob_out.cbData)
    map(ctypes.windll.kernel32.LocalFree, [desc, blob_out.pbData])

    return buffer_out.raw


def epoch_from_webkit(webkit_timestamp):
    epoch_time = 0
    chrome_epoch_start = 11644473600  # 1601.01.01
    webkit_timestamp = webkit_timestamp / 1000000
    if webkit_timestamp > chrome_epoch_start:
        epoch_time = int(webkit_timestamp - chrome_epoch_start)
    return epoch_time


def to_domain(domain: str) -> str:
    """formats domain as Netscape cookie format spec"""
    if not domain.startswith("."):
        if len(domain.split(".")) > 2:
            domain = "." + ".".join(domain.split(".")[-2:])
        else:
            domain = "." + domain
    else:
        domain = "." + ".".join(domain.split(".")[-2:])
    return domain



def to_boolean(flag: str) -> str:
    return "TRUE" if flag == 1 else "FALSE"


if __name__ == '__main__':
    get_chrome_cookies()
