import hashlib
import os
from base64 import urlsafe_b64encode
from datetime import date
from time import mktime

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def aes_gcm_128_encrypt(key, plaintext, associated_data):
    iv = os.urandom(12)
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, min_tag_length=16),
    ).encryptor()
    encryptor.authenticate_additional_data(associated_data)
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return (iv, ciphertext, encryptor.tag)


def aes_gcm_128_decrypt(key, associated_data, iv, ciphertext, tag):
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag, min_tag_length=16),
    ).decryptor()
    decryptor.authenticate_additional_data(associated_data)
    return decryptor.update(ciphertext) + decryptor.finalize()


def md5(code: str) -> str:
    # md5 encryption algorithm
    code = code.encode()
    md5s = hashlib.md5()
    md5s.update(code)
    codes = md5s.hexdigest()

    return codes


def get_file_md5(file_path: str) -> str:
    '''Compute file MD5, assumes it is a file'''
    myhash = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            b = f.read(8192)
            if not b:
                break
            myhash.update(b)

    return myhash.hexdigest()


def try_rename(path: str, new_path: str) -> str:
    '''Try to rename a file and try to avoid naming conflicts (by appending an incrementing number), return the final path'''
    final_path = new_path
    if os.path.exists(new_path):
        i = 1
        while os.path.exists(new_path + str(i)):
            i += 1

        final_path = new_path + str(i)

    os.rename(path, final_path)
    return final_path


def get_today_timestamp():
    '''Timestamp of today's 0:00 relative to the local machine's local time'''
    return int(mktime(date.today().timetuple()))


def parse_version(s: str) -> 'list[int]':
    '''Parse version number'''
    s_number = "".join(x for x in s if x.isdigit() or x == '.')
    return list(map(int, [x for x in s_number.split('.') if x != '']))


def join_path(*parts: str, sep: str = '/', start_sep: bool = True, end_sep: bool = False) -> str:
    '''Join paths using sep as separator; if start_sep, add sep at the beginning; if end_sep, add sep at the end'''
    path = sep.join(part.strip(sep) for part in parts)
    if not path:
        return sep if start_sep or end_sep else ''
    if start_sep:
        path = sep + path
    if end_sep:
        path = path + sep
    return path


def secure_link_md5(plaintext: str) -> str:
    '''Generate the MD5 for an Nginx secure link'''
    return urlsafe_b64encode(hashlib.md5(plaintext.encode()).digest()).rstrip(b'=').decode()
