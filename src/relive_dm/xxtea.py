import struct

_DELTA = 0x9E3779B9


def _long2str(v, w):
    n = (len(v) - 1) << 2
    if w:
        m = v[-1]
        if (m < n - 3) or (m > n):
            return ""
        n = m
    s = struct.pack("<%iL" % len(v), *v)
    return s[0:n] if w else s


def _str2long(s, w):
    n = len(s)
    m = (4 - (n & 3) & 3) + n
    s = s.ljust(m, b"\0")
    v = list(struct.unpack("<%iL" % (m >> 2), s))
    if w:
        v.append(n)
    return v


def encrypt_xxtea(data: bytes, key=b"j8onLz05ce37gmbA"):
    if data == "":
        return data
    v = _str2long(data, True)
    k = _str2long(key.ljust(16, b"\0"), False)
    n = len(v) - 1
    z = v[n]
    y = v[0]
    sum = 0
    q = 6 + 52 // (n + 1)
    while q > 0:
        sum = (sum + _DELTA) & 0xFFFFFFFF
        e = sum >> 2 & 3
        for p in range(n):
            y = v[p + 1]
            v[p] = (
                v[p]
                + (
                    (z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)
                    ^ (sum ^ y) + (k[p & 3 ^ e] ^ z)
                )
            ) & 0xFFFFFFFF
            z = v[p]
        y = v[0]
        v[n] = (
            v[n]
            + ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[n & 3 ^ e] ^ z))
        ) & 0xFFFFFFFF
        z = v[n]
        q -= 1
    return _long2str(v, False)


def decrypt_xxtea(data: bytes, key=b"j8onLz05ce37gmbA"):
    if data == b"":
        return data
    v = _str2long(data, False)
    k = _str2long(key.ljust(16, b"\0"), False)
    n = len(v) - 1
    z = v[n]
    y = v[0]
    q = 6 + 52 // (n + 1)
    sum = (q * _DELTA) & 0xFFFFFFFF
    while sum != 0:
        e = sum >> 2 & 3
        for p in range(n, 0, -1):
            z = v[p - 1]
            v[p] = (
                v[p]
                - (
                    (z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)
                    ^ (sum ^ y) + (k[p & 3 ^ e] ^ z)
                )
            ) & 0xFFFFFFFF
            y = v[p]
        z = v[n]
        v[0] = (
            v[0]
            - ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[0 & 3 ^ e] ^ z))
        ) & 0xFFFFFFFF
        y = v[0]
        sum = (sum - _DELTA) & 0xFFFFFFFF
    return _long2str(v, True)


def decrypt_xxtea_if_header(data: bytes, key=b"j8onLz05ce37gmbA") -> bytes:
    if data.startswith(b"XXTEA"):
        return decrypt_xxtea(data[5:], key)
    else:
        return data
