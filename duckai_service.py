import requests
from playwright.sync_api import sync_playwright
import json
import base_get_channel as channel
from typing import Optional, Dict
import time
import execjs
from datetime import datetime, timedelta
# 禁用 SSL 警告
import urllib3
import traceback
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

debug = True
last_request_time = 0  # 上次请求的时间戳
cache_duration = 14400  # 缓存有效期，单位：秒 (4小时)
'''用于存储缓存的模型数据'''
cached_models = {
    "object": "list",
    "data": [],
    "version": "1.0.5",
    "provider": "DuckAI",
    "name": "DuckAI",
    "default_locale": "zh-CN",
    "status": True,
    "time": "20250618"
}

'''基础模型'''
base_model = "gpt-4o-mini"
# 全局变量：存储所有模型的统计信息
# 格式：{model_name: {"calls": 调用次数, "fails": 失败次数, "last_fail": 最后失败时间}}
MODEL_STATS: Dict[str, Dict] = {}

js_code = """
var CryptoJS = CryptoJS || (function (Math, undefined) {
    var crypto;
    if (typeof window !== 'undefined' && window.crypto) {
        crypto = window.crypto;
    }
    if (typeof self !== 'undefined' && self.crypto) {
        crypto = self.crypto;
    }
    if (typeof globalThis !== 'undefined' && globalThis.crypto) {
        crypto = globalThis.crypto;
    }
    if (!crypto && typeof window !== 'undefined' && window.msCrypto) {
        crypto = window.msCrypto;
    }
    if (!crypto && typeof global !== 'undefined' && global.crypto) {
        crypto = global.crypto;
    }
    if (!crypto && typeof require === 'function') {
        try {
            crypto = require('crypto');
        } catch (err) {
        }
    }
    var cryptoSecureRandomInt = function () {
        if (crypto) {
            if (typeof crypto.getRandomValues === 'function') {
                try {
                    return crypto.getRandomValues(new Uint32Array(1))[0];
                } catch (err) {
                }
            }
            if (typeof crypto.randomBytes === 'function') {
                try {
                    return crypto.randomBytes(4).readInt32LE();
                } catch (err) {
                }
            }
        }
        throw new Error('Native crypto module could not be used to get secure random number.');
    };
    var create = Object.create || (function () {
        function F() {
        }

        return function (obj) {
            var subtype;
            F.prototype = obj;
            subtype = new F();
            F.prototype = null;
            return subtype;
        };
    }());
    var C = {};
    var C_lib = C.lib = {};
    var Base = C_lib.Base = (function () {
        return {
            extend: function (overrides) {
                var subtype = create(this);
                if (overrides) {
                    subtype.mixIn(overrides);
                }
                if (!subtype.hasOwnProperty('init') || this.init === subtype.init) {
                    subtype.init = function () {
                        subtype.$super.init.apply(this, arguments);
                    };
                }
                subtype.init.prototype = subtype;
                subtype.$super = this;
                return subtype;
            }, create: function () {
                var instance = this.extend();
                instance.init.apply(instance, arguments);
                return instance;
            }, init: function () {
            }, mixIn: function (properties) {
                for (var propertyName in properties) {
                    if (properties.hasOwnProperty(propertyName)) {
                        this[propertyName] = properties[propertyName];
                    }
                }
                if (properties.hasOwnProperty('toString')) {
                    this.toString = properties.toString;
                }
            }, clone: function () {
                return this.init.prototype.extend(this);
            }
        };
    }());
    var WordArray = C_lib.WordArray = Base.extend({
        init: function (words, sigBytes) {
            words = this.words = words || [];
            if (sigBytes != undefined) {
                this.sigBytes = sigBytes;
            } else {
                this.sigBytes = words.length * 4;
            }
        }, toString: function (encoder) {
            return (encoder || Hex).stringify(this);
        }, concat: function (wordArray) {
            var thisWords = this.words;
            var thatWords = wordArray.words;
            var thisSigBytes = this.sigBytes;
            var thatSigBytes = wordArray.sigBytes;
            this.clamp();
            if (thisSigBytes % 4) {
                for (var i = 0; i < thatSigBytes; i++) {
                    var thatByte = (thatWords[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
                    thisWords[(thisSigBytes + i) >>> 2] |= thatByte << (24 - ((thisSigBytes + i) % 4) * 8);
                }
            } else {
                for (var j = 0; j < thatSigBytes; j += 4) {
                    thisWords[(thisSigBytes + j) >>> 2] = thatWords[j >>> 2];
                }
            }
            this.sigBytes += thatSigBytes;
            return this;
        }, clamp: function () {
            var words = this.words;
            var sigBytes = this.sigBytes;
            words[sigBytes >>> 2] &= 0xffffffff << (32 - (sigBytes % 4) * 8);
            words.length = Math.ceil(sigBytes / 4);
        }, clone: function () {
            var clone = Base.clone.call(this);
            clone.words = this.words.slice(0);
            return clone;
        }, random: function (nBytes) {
            var words = [];
            var r = (function (m_w) {
                var m_w = m_w;
                var m_z = 0x3ade68b1;
                var mask = 0xffffffff;
                return function () {
                    m_z = (0x9069 * (m_z & 0xFFFF) + (m_z >> 0x10)) & mask;
                    m_w = (0x4650 * (m_w & 0xFFFF) + (m_w >> 0x10)) & mask;
                    var result = ((m_z << 0x10) + m_w) & mask;
                    result /= 0x100000000;
                    result += 0.5;
                    return result * (Math.random() > .5 ? 1 : -1);
                }
            });
            var RANDOM = false, _r;
            try {
                cryptoSecureRandomInt();
                RANDOM = true;
            } catch (err) {
            }
            for (var i = 0, rcache; i < nBytes; i += 4) {
                if (!RANDOM) {
                    _r = r((rcache || Math.random()) * 0x100000000);
                    rcache = _r() * 0x3ade67b7;
                    words.push((_r() * 0x100000000) | 0);
                    continue;
                }
                words.push(cryptoSecureRandomInt());
            }
            return new WordArray.init(words, nBytes);
        }
    });
    var C_enc = C.enc = {};
    var Hex = C_enc.Hex = {
        stringify: function (wordArray) {
            var words = wordArray.words;
            var sigBytes = wordArray.sigBytes;
            var hexChars = [];
            for (var i = 0; i < sigBytes; i++) {
                var bite = (words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
                hexChars.push((bite >>> 4).toString(16));
                hexChars.push((bite & 0x0f).toString(16));
            }
            return hexChars.join('');
        }, parse: function (hexStr) {
            var hexStrLength = hexStr.length;
            var words = [];
            for (var i = 0; i < hexStrLength; i += 2) {
                words[i >>> 3] |= parseInt(hexStr.substr(i, 2), 16) << (24 - (i % 8) * 4);
            }
            return new WordArray.init(words, hexStrLength / 2);
        }
    };
    var Latin1 = C_enc.Latin1 = {
        stringify: function (wordArray) {
            var words = wordArray.words;
            var sigBytes = wordArray.sigBytes;
            var latin1Chars = [];
            for (var i = 0; i < sigBytes; i++) {
                var bite = (words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
                latin1Chars.push(String.fromCharCode(bite));
            }
            return latin1Chars.join('');
        }, parse: function (latin1Str) {
            var latin1StrLength = latin1Str.length;
            var words = [];
            for (var i = 0; i < latin1StrLength; i++) {
                words[i >>> 2] |= (latin1Str.charCodeAt(i) & 0xff) << (24 - (i % 4) * 8);
            }
            return new WordArray.init(words, latin1StrLength);
        }
    };
    var Utf8 = C_enc.Utf8 = {
        stringify: function (wordArray) {
            try {
                return decodeURIComponent(escape(Latin1.stringify(wordArray)));
            } catch (e) {
                throw new Error('Malformed UTF-8 data');
            }
        }, parse: function (utf8Str) {
            return Latin1.parse(unescape(encodeURIComponent(utf8Str)));
        }
    };
    var BufferedBlockAlgorithm = C_lib.BufferedBlockAlgorithm = Base.extend({
        reset: function () {
            this._data = new WordArray.init();
            this._nDataBytes = 0;
        }, _append: function (data) {
            if (typeof data == 'string') {
                data = Utf8.parse(data);
            }
            this._data.concat(data);
            this._nDataBytes += data.sigBytes;
        }, _process: function (doFlush) {
            var processedWords;
            var data = this._data;
            var dataWords = data.words;
            var dataSigBytes = data.sigBytes;
            var blockSize = this.blockSize;
            var blockSizeBytes = blockSize * 4;
            var nBlocksReady = dataSigBytes / blockSizeBytes;
            if (doFlush) {
                nBlocksReady = Math.ceil(nBlocksReady);
            } else {
                nBlocksReady = Math.max((nBlocksReady | 0) - this._minBufferSize, 0);
            }
            var nWordsReady = nBlocksReady * blockSize;
            var nBytesReady = Math.min(nWordsReady * 4, dataSigBytes);
            if (nWordsReady) {
                for (var offset = 0; offset < nWordsReady; offset += blockSize) {
                    this._doProcessBlock(dataWords, offset);
                }
                processedWords = dataWords.splice(0, nWordsReady);
                data.sigBytes -= nBytesReady;
            }
            return new WordArray.init(processedWords, nBytesReady);
        }, clone: function () {
            var clone = Base.clone.call(this);
            clone._data = this._data.clone();
            return clone;
        }, _minBufferSize: 0
    });
    var Hasher = C_lib.Hasher = BufferedBlockAlgorithm.extend({
        cfg: Base.extend(),
        init: function (cfg) {
            this.cfg = this.cfg.extend(cfg);
            this.reset();
        }, reset: function () {
            BufferedBlockAlgorithm.reset.call(this);
            this._doReset();
        }, update: function (messageUpdate) {
            this._append(messageUpdate);
            this._process();
            return this;
        }, finalize: function (messageUpdate) {
            if (messageUpdate) {
                this._append(messageUpdate);
            }
            var hash = this._doFinalize();
            return hash;
        }, blockSize: 512 / 32,
        _createHelper: function (hasher) {
            return function (message, cfg) {
                return new hasher.init(cfg).finalize(message);
            };
        }, _createHmacHelper: function (hasher) {
            return function (message, key) {
                return new C_algo.HMAC.init(hasher, key).finalize(message);
            };
        }
    });
    var C_algo = C.algo = {};
    return C;
}(Math));

(function () {
    var C = CryptoJS;
    var C_lib = C.lib;
    var WordArray = C_lib.WordArray;
    var C_enc = C.enc;
    var Base64 = C_enc.Base64 = {
        stringify: function (wordArray) {
            var words = wordArray.words;
            var sigBytes = wordArray.sigBytes;
            var map = this._map;
            wordArray.clamp();
            var base64Chars = [];
            for (var i = 0; i < sigBytes; i += 3) {
                var byte1 = (words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
                var byte2 = (words[(i + 1) >>> 2] >>> (24 - ((i + 1) % 4) * 8)) & 0xff;
                var byte3 = (words[(i + 2) >>> 2] >>> (24 - ((i + 2) % 4) * 8)) & 0xff;
                var triplet = (byte1 << 16) | (byte2 << 8) | byte3;
                for (var j = 0;
                     (j < 4) && (i + j * 0.75 < sigBytes); j++) {
                    base64Chars.push(map.charAt((triplet >>> (6 * (3 - j))) & 0x3f));
                }
            }
            var paddingChar = map.charAt(64);
            if (paddingChar) {
                while (base64Chars.length % 4) {
                    base64Chars.push(paddingChar);
                }
            }
            return base64Chars.join('');
        }, parse: function (base64Str) {
            var base64StrLength = base64Str.length;
            var map = this._map;
            var reverseMap = this._reverseMap;
            if (!reverseMap) {
                reverseMap = this._reverseMap = [];
                for (var j = 0; j < map.length; j++) {
                    reverseMap[map.charCodeAt(j)] = j;
                }
            }
            var paddingChar = map.charAt(64);
            if (paddingChar) {
                var paddingIndex = base64Str.indexOf(paddingChar);
                if (paddingIndex !== -1) {
                    base64StrLength = paddingIndex;
                }
            }
            return parseLoop(base64Str, base64StrLength, reverseMap);
        }, _map: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
    };

    function parseLoop(base64Str, base64StrLength, reverseMap) {
        var words = [];
        var nBytes = 0;
        for (var i = 0; i < base64StrLength; i++) {
            if (i % 4) {
                var bits1 = reverseMap[base64Str.charCodeAt(i - 1)] << ((i % 4) * 2);
                var bits2 = reverseMap[base64Str.charCodeAt(i)] >>> (6 - (i % 4) * 2);
                words[nBytes >>> 2] |= (bits1 | bits2) << (24 - (nBytes % 4) * 8);
                nBytes++;
            }
        }
        return WordArray.create(words, nBytes);
    }
}());

(function (Math) {
    var C = CryptoJS;
    var C_lib = C.lib;
    var WordArray = C_lib.WordArray;
    var Hasher = C_lib.Hasher;
    var C_algo = C.algo;
    var H = [];
    var K = [];
    (function () {
        function isPrime(n) {
            var sqrtN = Math.sqrt(n);
            for (var factor = 2; factor <= sqrtN; factor++) {
                if (!(n % factor)) {
                    return false;
                }
            }
            return true;
        }

        function getFractionalBits(n) {
            return ((n - (n | 0)) * 0x100000000) | 0;
        }

        var n = 2;
        var nPrime = 0;
        while (nPrime < 64) {
            if (isPrime(n)) {
                if (nPrime < 8) {
                    H[nPrime] = getFractionalBits(Math.pow(n, 1 / 2));
                }
                K[nPrime] = getFractionalBits(Math.pow(n, 1 / 3));
                nPrime++;
            }
            n++;
        }
    }());
    var W = [];
    var SHA256 = C_algo.SHA256 = Hasher.extend({
        _doReset: function () {
            this._hash = new WordArray.init(H.slice(0));
        }, _doProcessBlock: function (M, offset) {
            var H = this._hash.words;
            var a = H[0];
            var b = H[1];
            var c = H[2];
            var d = H[3];
            var e = H[4];
            var f = H[5];
            var g = H[6];
            var h = H[7];
            for (var i = 0; i < 64; i++) {
                if (i < 16) {
                    W[i] = M[offset + i] | 0;
                } else {
                    var gamma0x = W[i - 15];
                    var gamma0 = ((gamma0x << 25) | (gamma0x >>> 7)) ^ ((gamma0x << 14) | (gamma0x >>> 18)) ^ (gamma0x >>> 3);
                    var gamma1x = W[i - 2];
                    var gamma1 = ((gamma1x << 15) | (gamma1x >>> 17)) ^ ((gamma1x << 13) | (gamma1x >>> 19)) ^ (gamma1x >>> 10);
                    W[i] = gamma0 + W[i - 7] + gamma1 + W[i - 16];
                }
                var ch = (e & f) ^ (~e & g);
                var maj = (a & b) ^ (a & c) ^ (b & c);
                var sigma0 = ((a << 30) | (a >>> 2)) ^ ((a << 19) | (a >>> 13)) ^ ((a << 10) | (a >>> 22));
                var sigma1 = ((e << 26) | (e >>> 6)) ^ ((e << 21) | (e >>> 11)) ^ ((e << 7) | (e >>> 25));
                var t1 = h + sigma1 + ch + K[i] + W[i];
                var t2 = sigma0 + maj;
                h = g;
                g = f;
                f = e;
                e = (d + t1) | 0;
                d = c;
                c = b;
                b = a;
                a = (t1 + t2) | 0;
            }
            H[0] = (H[0] + a) | 0;
            H[1] = (H[1] + b) | 0;
            H[2] = (H[2] + c) | 0;
            H[3] = (H[3] + d) | 0;
            H[4] = (H[4] + e) | 0;
            H[5] = (H[5] + f) | 0;
            H[6] = (H[6] + g) | 0;
            H[7] = (H[7] + h) | 0;
        }, _doFinalize: function () {
            var data = this._data;
            var dataWords = data.words;
            var nBitsTotal = this._nDataBytes * 8;
            var nBitsLeft = data.sigBytes * 8;
            dataWords[nBitsLeft >>> 5] |= 0x80 << (24 - nBitsLeft % 32);
            dataWords[(((nBitsLeft + 64) >>> 9) << 4) + 14] = Math.floor(nBitsTotal / 0x100000000);
            dataWords[(((nBitsLeft + 64) >>> 9) << 4) + 15] = nBitsTotal;
            data.sigBytes = dataWords.length * 4;
            this._process();
            return this._hash;
        }, clone: function () {
            var clone = Hasher.clone.call(this);
            clone._hash = this._hash.clone();
            return clone;
        }
    });
    C.SHA256 = Hasher._createHelper(SHA256);
    C.HmacSHA256 = Hasher._createHmacHelper(SHA256);
}(Math));

function SHA256_Encrypt(word) {
    return CryptoJS.SHA256(word).toString(CryptoJS.enc.Base64);
}


const jsdom = require("jsdom");
const {
    JSDOM
} = jsdom;
const dom = new JSDOM(` < !DOCTYPE html > <p > Hello world < /p>`,{
    url:'https://m.tujia.com/hotel_shenzhen/'
});
window = dom.window;
document = window.document;
navigator = {
    appCodeName: "Mozilla",
    appMinorVersion: "0",
    appName: "Netscape",
    appVersion: "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    browserLanguage: "zh-CN",
    cookieEnabled: true,
    cpuClass: "x86",
    language: "zh-CN",
    maxTouchPoints: 0,
    msManipulationViewsEnabled: true,
    msMaxTouchPoints: 0,
    msPointerEnabled: true,
    onLine: true,
    platform: "Win32",
    pointerEnabled: true,
    product: "Gecko",
    systemLanguage: "zh-CN",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    userLanguage: "zh-CN",
    vendor: "",
    vendorSub: "",
    brands:[{"brand":"Google Chrome","version":"135"},{"brand":"Not-A.Brand","version":"8"},{"brand":"Chromium","version":"135"}],
    webdriver: false
}

function dd(word) {
    a = eval(atob(word))
    console.log(a)
    result = btoa(JSON.stringify({
        "server_hashes": [a['server_hashes'][0], a['server_hashes'][1]],
        "client_hashes": ["SFGRWX9mxQ47bYmycqmSySnzSAgk5BzgeRkorNyb6KQ=", SHA256_Encrypt(a['client_hashes'][1])],
        "signals": {},
        "meta": {"v": "3", "challenge_id": a['meta']['challenge_id']},"timestamp":Date.now()+"",
        "origin": "https://duckduckgo.com",
        "stack": "Error\nat bn (https://duckduckgo.com/dist/wpm.chat.16d105cd2e432a85e59b.js:1:74803)\nat async dispatchServiceInitialVQD (https://duckduckgo.com/dist/wpm.chat.16d105cd2e432a85e59b.js:1:99529)"}
    ))
    return result
}
word = 'KGZ1bmN0aW9uKCl7Y29uc3QgXzB4NDk0OTY2PV8weDE4Nzg7KGZ1bmN0aW9uKF8weDNiYmQwYixfMHgyMzRjNjgpe2NvbnN0IF8weDQwZjY0Nj1fMHgxODc4LF8weDUzYjcwYz1fMHgzYmJkMGIoKTt3aGlsZSghIVtdKXt0cnl7Y29uc3QgXzB4M2ZkYjgyPS1wYXJzZUludChfMHg0MGY2NDYoMHgxZjMpKS8weDErLXBhcnNlSW50KF8weDQwZjY0NigweDFmOCkpLzB4MitwYXJzZUludChfMHg0MGY2NDYoMHgyMDIpKS8weDMrLXBhcnNlSW50KF8weDQwZjY0NigweDFmNCkpLzB4NCstcGFyc2VJbnQoXzB4NDBmNjQ2KDB4MWY5KSkvMHg1Ky1wYXJzZUludChfMHg0MGY2NDYoMHgxZmMpKS8weDYrcGFyc2VJbnQoXzB4NDBmNjQ2KDB4MWYwKSkvMHg3KihwYXJzZUludChfMHg0MGY2NDYoMHgyMDMpKS8weDgpO2lmKF8weDNmZGI4Mj09PV8weDIzNGM2OClicmVhaztlbHNlIF8weDUzYjcwY1sncHVzaCddKF8weDUzYjcwY1snc2hpZnQnXSgpKTt9Y2F0Y2goXzB4ZjJmYmRhKXtfMHg1M2I3MGNbJ3B1c2gnXShfMHg1M2I3MGNbJ3NoaWZ0J10oKSk7fX19KF8weDIzMDEsMHhhMjliYSkpO2Z1bmN0aW9uIF8weDE4NzgoXzB4OTViZGEwLF8weDQwZTkyMil7Y29uc3QgXzB4MjMwMWU0PV8weDIzMDEoKTtyZXR1cm4gXzB4MTg3OD1mdW5jdGlvbihfMHgxODc4MDQsXzB4MzgxMDA4KXtfMHgxODc4MDQ9XzB4MTg3ODA0LTB4MWVmO2xldCBfMHgzMmVlNjg9XzB4MjMwMWU0W18weDE4NzgwNF07cmV0dXJuIF8weDMyZWU2ODt9LF8weDE4NzgoXzB4OTViZGEwLF8weDQwZTkyMik7fWZ1bmN0aW9uIF8weDIzMDEoKXtjb25zdCBfMHg0YjNjOGQ9WycyNjQzOTg1VXp2Z0xDJywnbWFwJywnY3JlYXRlRWxlbWVudCcsJzIwOTQ3MzhvZFNabUMnLCdicmFuZHMnLCcxNzUwMDg5NzI5Mzk4JywneVBpa3ozd2M1Z0V2OEw2NGE5ZW45MjNBamtlaXVwbDUva1ZSWW9tcXcxND0nLCdqb2luJywnXHgyMjt2PVx4MjInLCczMzUxMzY2QXFJdUtlJywnMzA2NFV0RUJlRCcsJ3VzZXJBZ2VudERhdGEnLCc1emdHTDkwVHhoQkY2RHREbDkzRm95cS9BK2ZKZWJoUW5OS1A4a2JuU2drPScsJ3F1ZXJ5U2VsZWN0b3JBbGwnLCc8cD48ZGl2PjwvcD48cD48L2RpdicsJzU5OTY5bGJjREJCJywndmVyc2lvbicsJ2RpdicsJzEzMTkyNzRyempZdUsnLCc0OTY5NjIwQkh6WkNuJywnaW5uZXJIVE1MJywnYnJhbmQnLCdsZW5ndGgnLCc1ODUyODRvS1BkQ2InXTtfMHgyMzAxPWZ1bmN0aW9uKCl7cmV0dXJuIF8weDRiM2M4ZDt9O3JldHVybiBfMHgyMzAxKCk7fXJldHVybnsnc2VydmVyX2hhc2hlcyc6W18weDQ5NDk2NigweDIwNSksXzB4NDk0OTY2KDB4MWZmKV0sJ2NsaWVudF9oYXNoZXMnOltuYXZpZ2F0b3JbJ3VzZXJBZ2VudCddKyhuYXZpZ2F0b3JbXzB4NDk0OTY2KDB4MjA0KV0/bmF2aWdhdG9yW18weDQ5NDk2NigweDIwNCldW18weDQ5NDk2NigweDFmZCldW18weDQ5NDk2NigweDFmYSldKF8weDQ5NWRiNz0+J1x4MjInK18weDQ5NWRiN1tfMHg0OTQ5NjYoMHgxZjYpXStfMHg0OTQ5NjYoMHgyMDEpK18weDQ5NWRiN1tfMHg0OTQ5NjYoMHgxZjEpXSsnXHgyMicpW18weDQ5NDk2NigweDIwMCldKCcsXHgyMCcpOicnKSwoZnVuY3Rpb24oKXtjb25zdCBfMHgzODI2YTA9XzB4NDk0OTY2LF8weDFmZjFmNj1kb2N1bWVudFtfMHgzODI2YTAoMHgxZmIpXShfMHgzODI2YTAoMHgxZjIpKTtyZXR1cm4gXzB4MWZmMWY2Wydpbm5lckhUTUwnXT1fMHgzODI2YTAoMHgxZWYpLFN0cmluZygweDFjYjArXzB4MWZmMWY2W18weDM4MjZhMCgweDFmNSldW18weDM4MjZhMCgweDFmNyldKl8weDFmZjFmNltfMHgzODI2YTAoMHgyMDYpXSgnKicpW18weDM4MjZhMCgweDFmNyldKTt9KCkpXSwnc2lnbmFscyc6e30sJ21ldGEnOnsndic6JzMnLCdjaGFsbGVuZ2VfaWQnOicxODQ4NTM5MDhmYTQ3ODBlMzcyNmE4ZTVjNmFhY2ZlYTkzOGQ4ZmMzMmJjOGRmODc1MDM4Yjk3YTI1Yzk1MzBiaDhqYnQnLCd0aW1lc3RhbXAnOl8weDQ5NDk2NigweDFmZSl9fTt9KSgp'

console.log(dd(word))
"""


def reload_check():
    """
    清除 cached_models 中的 data，重新加载模型数据，并获取最优模型
    """
    global cached_models
    # 清除 cached_models 中的 data
    cached_models = {
        "object": "list",
        "data": [],
        "version": "1.0.4",
        "provider": "DuckAI",
        "name": "DuckAI",
        "default_locale": "zh-CN",
        "status": True,
        "time": "20250516"
    }

    # 重新加载模型数据
    get_models()

    # 获取最优模型
    best_model = get_auto_model()
    if debug:
        print(f"最优模型: {best_model}")
    return best_model


def record_call(model_name: str, success: bool = True) -> None:
    """
    记录模型调用情况
    Args:
        model_name: 模型名称
        success: 调用是否成功
    """
    global MODEL_STATS
    if model_name not in MODEL_STATS:
        MODEL_STATS[model_name] = {"calls": 0, "fails": 0, "last_fail": None}

    stats = MODEL_STATS[model_name]
    stats["calls"] += 1
    if not success:
        stats["fails"] += 1
        stats["last_fail"] = datetime.now()


def get_auto_model(cooldown_seconds: int = 300) -> str:
    """异步获取最优模型"""
    try:
        if not MODEL_STATS:
            get_models()

        best_model = "gpt-4o-mini"
        best_rate = -1.0
        now = datetime.now()

        for name, stats in MODEL_STATS.items():
            if stats.get("last_fail") and (now - stats["last_fail"]) < timedelta(seconds=cooldown_seconds):
                continue

            total_calls = stats["calls"]
            if total_calls > 0:
                success_rate = (total_calls - stats["fails"]) / total_calls
                if success_rate > best_rate:
                    best_rate = success_rate
                    best_model = name

        default_model = best_model or base_model
        if debug:
            print(f"选择模型: {default_model}")
        return default_model
    except Exception as e:
        if debug:
            print(f"模型选择错误: {e}")
        return base_model


def get_models():
    """model data retrieval with thread safety"""
    global cached_models, last_request_time
    current_time = time.time()
    if (current_time - last_request_time) > cache_duration:
        try:
            if debug:
                print(f"will get model ")
            # Update timestamp before awaiting to prevent concurrent updates
            get_model_impl_by_playwright()
            last_request_time = current_time
            if debug:
                print(f"success get model ")
        except Exception as e:
            if debug:
                print(f"000000---{e}")
            pass

    return json.dumps(cached_models)


def parser_models_info_form_page(page):
    global cached_models
    models = page.query_selector_all('ul[role="radiogroup"] > li')

    # 创建现有模型的 ID 集合用于快速查找
    existing_ids = {item["id"] for item in cached_models['data']}
    if debug:
        print(existing_ids)
    result = []
    # 确保有内容时更新
    is_update = False
    for model in models:
        # 使用更精确的选择器
        name_element = model.query_selector('.J58ouJfofMIxA2Ukt6lA')
        description_element = model.query_selector('.tDjqHxDUIeGL37tpvoSI')
        # 模型真实名字
        value = model.query_selector('input').get_attribute('value')
        # 确保有效
        if not name_element or not value:
            continue

        # 模型名字
        name = name_element.inner_text()
        description = description_element.inner_text() if description_element else ""
        # 确定描述供应商
        owned_by = channel.get_channel_company(value, description)
        # 生成新模型数据
        new_model = {
            "id": value,
            "object": "model",
            "model": value,
            "created": int(time.time() * 1000),  # 使用当前时间戳
            "name": name,
            "support": "text",
            "owned_by": owned_by,
            "description": name
        }
        if debug:
            print(f"new_model: {new_model}")
        # 记录成功
        record_call(value)
        if debug:
            print(f"after record_call")
        # 检查是否已存在相同 ID 的模型
        if new_model['id'] in existing_ids:
            # 更新已存在的模型数据
            for idx, item in enumerate(cached_models['data']):
                if item['id'] == new_model['id']:
                    cached_models['data'][idx] = new_model  # 完全替换旧数据
                    break
        else:
            # 添加新模型到缓存
            cached_models['data'].append(new_model)
        if debug:
            print(f"解析cached_models模型信息: {cached_models}")

        is_updated = True

    # 仅在检测到更新时刷新时间戳
    if is_updated:
        cached_models['time'] = int(time.time() * 1000)
    return json.dumps(cached_models, ensure_ascii=False)


def get_model_impl_by_playwright():
    """
        从网页获取获取模型
    """
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # headless=False 表示显示浏览器窗口
        context = browser.new_context()
        page = browser.new_page()

        try:
            # 导航到网页
            page.goto("https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat&duckai=1")

            if debug:
                print("点击试试看\r\n",page.content())
            # 点击试试看
            # page.locator("//div[@class='G7rDHS2k8fykjYYMbnTg']/button").click()
            tool_selector = "//div[@class='G7rDHS2k8fykjYYMbnTg']/button"
            page.wait_for_selector(tool_selector, state="visible")
            page.locator(tool_selector).click()

            if debug:
                print("点击我同意\r\n",page.content())
            # 点击我同意
            # page.locator("//div[@class='G7rDHS2k8fykjYYMbnTg NHrnRvFtkZSdVRA6P3kD']/button").click()
            tool_selector = "//div[@class='G7rDHS2k8fykjYYMbnTg NHrnRvFtkZSdVRA6P3kD']/button"
            page.wait_for_selector(tool_selector, state="visible")
            page.locator(tool_selector).click()


            if debug:
                print("点击下拉框，出现5个AI工具\r\n",page.content())
            # 点击下拉框，出现5个AI工具
            # page.locator('//div[@class="eHTKOmyhnmDrrdAFuwDc"]/button').click()
            tool_selector = 'div.eHTKOmyhnmDrrdAFuwDc > button'
            page.wait_for_selector(tool_selector, state="visible", timeout=15000)
            page.locator(tool_selector).click(delay=500)

            # 等待所有模型加载完成
            page.wait_for_function(
                "document.querySelectorAll('ul[role=\"radiogroup\"] > li').length > 0",
                timeout=20000
            )

            if debug:
                print("解析模型信息\r\n",page.content())
            # 解析模型信息
            if debug:
                print("\n开始解析模型信息...")
            parser_models_info_form_page(page)

        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            browser.close()


def is_model_available(model_id: str, cooldown_seconds: int = 300) -> bool:
    """
    判断模型是否在模型列表中且非最近失败的模型

    Args:
        model_id: 模型ID，需要检查的模型标识符
        cooldown_seconds: 失败冷却时间（秒），默认300秒

    Returns:
        bool: 如果模型可用返回True，否则返回False

    Note:
        - 当MODEL_STATS为空时会自动调用get_models()更新数据
        - 检查模型是否在冷却期内，如果在冷却期则返回False
    """
    global MODEL_STATS

    # 如果MODEL_STATS为空，加载模型数据
    if not MODEL_STATS:
        get_models()

    # 检查模型是否在统计信息中
    if model_id not in MODEL_STATS:
        return False

    # 检查是否在冷却期内
    stats = MODEL_STATS[model_id]
    if stats["last_fail"]:
        time_since_failure = datetime.now() - stats["last_fail"]
        if time_since_failure < timedelta(seconds=cooldown_seconds):
            return False

    return True


def get_model_by_autoupdate(model_id: Optional[str] = None, cooldown_seconds: int = 300) -> Optional[str]:
    """
    检查提供的model_id是否可用，如果不可用则返回成功率最高的模型

    Args:
        model_id: 指定的模型ID，可选参数
        cooldown_seconds: 失败冷却时间（秒），默认300秒

    Returns:
        str | None: 返回可用的模型ID，如果没有可用模型则返回None

    Note:
        - 当MODEL_STATS为空时会自动调用get_models()更新数据
        - 如果指定的model_id可用，则直接返回
        - 如果指定的model_id不可用，则返回成功率最高的模型
    """
    global MODEL_STATS

    # 如果MODEL_STATS为空，加载模型数据
    if not MODEL_STATS:
        get_models()

    # 如果提供了model_id且可用，直接返回
    if model_id and is_model_available(model_id, cooldown_seconds):
        return model_id

    # 否则返回成功率最高的可用模型
    return get_auto_model(cooldown_seconds=cooldown_seconds)


################################################################################################


def parse_response(response_text):
    """
    逐行解析
    """
    lines = response_text.split('\n')
    result = ""
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[len("data:"):])
            if "message" in data:
                result += data["message"]
    print(result)


def chat_completion_message(user_prompt, model=base_model,
                            system_message='You are a helpful assistant.',
                            user_id: str = "", session_id: str = "", default_host="duckduckgo.com"
                            , stream=False, temperature=0.3, max_tokens=1024, top_p=0.5, frequency_penalty=0,
                            presence_penalty=0):
    """
    单条消息请求: https://duckduckgo.com/duckchat/v1/chat
    """

    messages = [
        # 需要 system-> user
        {"role": "user", "content": system_message},
        {"role": "user", "content": user_prompt}
    ]
    return chat_completion_messages(messages=messages, model=model, default_host=default_host
                                    , user_id=user_id
                                    , session_id=session_id
                                    , stream=stream
                                    , temperature=temperature
                                    , max_tokens=max_tokens
                                    , top_p=top_p
                                    , frequency_penalty=frequency_penalty
                                    , presence_penalty=presence_penalty
                                    )


def chat_completion_messages(
        messages,
        model=base_model,
        default_host="duckduckgo.com",
        user_id: str = None,
        session_id: str = None,
        stream=False, temperature=0.3,
        max_tokens=1024, top_p=0.5,
        frequency_penalty=0, presence_penalty=0):
    try:
        # 确保model有效
        if not model or model == "auto":
            model = get_auto_model()
        else:
            model = get_model_by_autoupdate(model)
        if debug:
            print(f"chat_completion_messages 校准后的model: {model}")

        # makesure system-->user
        """将messages列表中所有role为system的条目改为user"""
        # print(messages)
        for msg in messages:
            if msg.get("role") == "system":
                msg["role"] = "user"
        # print(messages)
        # 调用 JavaScript 函数
        ctx = execjs.compile(js_code)

        headers = {
            "accept": "text/event-stream",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": f"https://{default_host}",
            "referer": f"https://{default_host}/",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "x-fe-signals": "eyJzdGFydCI6MTc1MDA4NzgwODY5NSwiZXZlbnRzIjpbeyJuYW1lIjoib25ib2FyZGluZ19pbXByZXNzaW9uXzEiLCJkZWx0YSI6Mzc5fSx7Im5hbWUiOiJvbmJvYXJkaW5nX2ltcHJlc3Npb25fMiIsImRlbHRhIjo2MzQxfSx7Im5hbWUiOiJvbmJvYXJkaW5nX2ZpbmlzaCIsImRlbHRhIjo5NjQ4fSx7Im5hbWUiOiJzdGFydE5ld0NoYXQiLCJkZWx0YSI6MTQ1Mjl9XSwiZW5kIjozMTY4OH0=",
            "x-fe-version": "serp_20250616_041534_ET-16d105cd2e432a85e59b",
            "x-vqd-4": "4-233475472251743453354969293510258779181",
            "x-vqd-hash-1": "eyJzZXJ2ZXJfaGFzaGVzIjpbIlE4NDNIRGVncGE5cDkxOHM5NzZqVjdzYzdRcXhRSzRYNTZXTGhJQzhRbkk9IiwiWSs1aGtVUStTdTQ1TFMreHhJZTZteHNIT3BxYnNhVGRWS1hqUjNRdVpBQT0iXSwiY2xpZW50X2hhc2hlcyI6WyJTRkdSV1g5bXhRNDdiWW15Y3FtU3lTbnpTQWdrNUJ6Z2VSa29yTnliNktRPSIsIkFRdVFZK1dlZlBPT1FrbkMrb1hPbnI2WUJmNlZMZXhuZGpCcW1rV0dJM1U9Il0sInNpZ25hbHMiOnt9LCJtZXRhIjp7InYiOiIzIiwiY2hhbGxlbmdlX2lkIjoiODIzMDljYzc1YTc3YWEwMjFlZDM5ZWJlZjI5ZTRlMmFmMWJlODYzZTczNGEwNGIzMWZmYWRlNTA5MTJjMDA1OGg4amJ0IiwidGltZXN0YW1wIjoiMTc1MDA4NzgyMzI0MSIsIm9yaWdpbiI6Imh0dHBzOi8vZHVja2R1Y2tnby5jb20iLCJzdGFjayI6IkVycm9yXG5hdCBibiAoaHR0cHM6Ly9kdWNrZHVja2dvLmNvbS9kaXN0L3dwbS5jaGF0LjE2ZDEwNWNkMmU0MzJhODVlNTliLmpzOjE6NzQ4MDMpXG5hdCBhc3luYyBkaXNwYXRjaFNlcnZpY2VJbml0aWFsVlFEIChodHRwczovL2R1Y2tkdWNrZ28uY29tL2Rpc3Qvd3BtLmNoYXQuMTZkMTA1Y2QyZTQzMmE4NWU1OWIuanM6MTo5OTUyOSkifX0="
        }
        cookies = {
            "dcm": "3",
            "dcs": "1"
        }
        url = "https://duckduckgo.com/duckchat/v1/chat"
        data = {
            "model": model,
            "metadata": {
                "toolChoice": {
                    "NewsSearch": False,
                    "VideosSearch": False,
                    "LocalSearch": False,
                    "WeatherForecast": False
                }
            },
            "messages": messages,
            "canUseTools": True
        }
        data = json.dumps(data, separators=(',', ':'))
        signalsword = {"start": int(time.time() * 1000), "events": [{"name": "onboarding_impression_1", "delta": 379},
                                                                    {"name": "onboarding_impression_2", "delta": 6341},
                                                                    {"name": "onboarding_finish", "delta": 9648},
                                                                    {"name": "startNewChat", "delta": 14529}],
                       "end": 31688}
        headers['x-fe-signals'] = base64.b64encode(json.dumps(signalsword).encode('utf-8')).decode('utf-8')
        res = requests.post(url, headers=headers, cookies=cookies, data=data)
        res.encoding = 'utf-8'
        # vqdhash = response.headers['x-vqd-hash-1']
        # vqd4 = response.headers['x-vqd-4']
        # headers['x-vqd-hash'] = ctx.call('dd', vqdhash)
        # headers['x-vqd-4'] = vqd4
        # data = json.loads(data)
        # data['messages'][0]['content'] = '1+1='
        # data = json.dumps(data, separators=(',', ':'))
        # signalsword["start"] = int(time.time() * 1000)
        # headers['x-fe-signals'] = base64.b64encode(json.dumps(signalsword).encode('utf-8')).decode('utf-8')
        # # response = requests.post(url, headers=headers, cookies=cookies, data=data, proxies=proxies)
        # response = requests.post(url, headers=headers, cookies=cookies, data=data)
        # response.encoding = 'utf-8'
        # print(response.text)

        if debug:
            print(res.text)

        # 解析响应内容
        final_content = ""
        if res.status_code == 200:
            for line in res.iter_lines(decode_unicode=True):
                # print(line)
                # print(line)
                # 检查 if 'data: [DONE]'在行中进行下一步动作
                if 'data: [DONE]' in line:
                    # 如果找到结束信号，退出循环
                    break
                elif line.startswith('data: '):  # 确保行以'data: '开头
                    data_json = line[6:]  # 删除行前缀'data: '
                    datax = json.loads(data_json)  # 解析JSON字符串为字典
                    if 'message' in datax:
                        final_content += datax['message']
                        # print( final_content)
            # # 保存最终的content结果
            # final_result = final_content
            if debug:
                print(final_content)
            return final_content
    except Exception as e:
        print(f"chat_completion_messages  使用模型[{model}]发生了异常：", e)
        traceback.print_exc()
    return ""


def mods(model, prompt):
    t1 = time.time()
    res = chat_completion_message(user_prompt=prompt, model=model)
    t2 = time.time()
    print(f"\r\n=======【{model}]===>【{t2 - t1} 秒】================\r\n--------本轮开始--------\r\n{res}\r\n--------本文结束--------")


# 测试代码
if __name__ == "__main__":
    debug = False
    time1 = time.time() * 1000
    result_json = get_models()
    time2 = time.time() * 1000
    print(f"耗时: {time2 - time1}\r\n获取模型列表:\r\n{result_json}")
    # result_json2 = get_models()
    # time3 = time.time() * 1000
    # print(f"耗时2: {time3 - time2}")
    # print(result_json2)
    #
    # print(f"获取自动模型1 get_model_by_autoupdate :{get_model_by_autoupdate('hello')}")
    # print(f"获取自动模型2 get_auto_model :{get_auto_model()}")
    # print(f"获取自动模型3 cached_models :{cached_models}")
    
    p = "你是谁?你使用的是什么模型?你的知识库截止到什么时间? "
    model_ids = [model['id'] for model in cached_models['data']]
    for id in model_ids:
        mods(id, p)
    # mes=[{"role": "system", "content": "you are a bot."},{"role": "user", "content": "Say this is a test!"},{"role":"assistant","content":"This is a test!"},{"role": "user", "content": "你擅长什么技能"}]
    # chat_completion_messages(mes,model="gpt-4o-mini")
