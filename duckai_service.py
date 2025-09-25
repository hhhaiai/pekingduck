import requests
import json
import base_get_channel as channel
from typing import Optional, Dict
import time
import execjs
import subprocess
import random
from datetime import datetime, timedelta
# 禁用 SSL 警告
import urllib3
import traceback
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 自定义 subprocess.Popen 类
class MySubprocessPopen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        super().__init__(encoding='UTF-8', *args, **kwargs)

# 替换默认的 subprocess.Popen
subprocess.Popen = MySubprocessPopen

debug = True
last_request_time = 0  # 上次请求的时间戳
cache_duration = 14400  # 缓存有效期，单位：秒 (4小时)
'''用于存储缓存的模型数据'''
cached_models = {
    "object": "list",
    "data": [
        {
            "id": "gpt-4o-mini",
            "object": "model",
            "model": "gpt-4o-mini",
            "created": int(time.time() * 1000),
            "name": "GPT-4o mini",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        },
        {
            "id": "gpt-5-mini",
            "object": "model",
            "model": "gpt-5-mini",
            "created": int(time.time() * 1000),
            "name": "GPT-5 mini",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        },
        {
            "id": "openai/gpt-oss-120b",
            "object": "model",
            "model": "openai/gpt-oss-120b",
            "created": int(time.time() * 1000),
            "name": "GPT-OSS 120B",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        },
        {
            "id": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "object": "model",
            "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "created": int(time.time() * 1000),
            "name": "Llama 4 Scout",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        },
        {
            "id": "claude-3-5-haiku-latest",
            "object": "model",
            "model": "claude-3-5-haiku-latest",
            "created": int(time.time() * 1000),
            "name": "Claude Haiku 3.5",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        },
        {
            "id": "mistralai/Mistral-Small-24B-Instruct-2501",
            "object": "model",
            "model": "mistralai/Mistral-Small-24B-Instruct-2501",
            "created": int(time.time() * 1000),
            "name": "Mistral Small 3",
            "support": "text",
            "owned_by": "DuckAI",
            "description": "High built-in moderation"
        }
    ],
    "version": "1.0.6",
    "provider": "DuckAI",
    "name": "DuckAI",
    "default_locale": "zh-CN",
    "status": True,
    "time": "20250925"
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
const dom = new JSDOM(` < !DOCTYPE html > <p > Hello world < /p>`, {
    url: 'https://m.tujia.com/hotel_shenzhen/'
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
    brands: [{"brand": "Google Chrome", "version": "135"}, {
        "brand": "Not-A.Brand",
        "version": "8"
    }, {"brand": "Chromium", "version": "135"}],
    webdriver: false
}
HTMLElement = function (arg) {

}
Element = function (arg) {

}
HTMLDivElement = function (arg) {

}
window.top = window

function dd(word) {
        eval(atob(word)).then(a => {
            var result = btoa(JSON.stringify({
                    "server_hashes": [a['server_hashes'][0], a['server_hashes'][1], a['server_hashes'][2]],
                    "client_hashes": ["lVnR41+B1QVgJ8wHa1GA6gqGBhJ9Vv3y+GHJGFzBfLc=", SHA256_Encrypt(a['client_hashes'][1]), SHA256_Encrypt(a['client_hashes'][2])],
                    "signals": {},
                    "meta": {
                        "v": "4", "challenge_id": a['meta']['challenge_id'], "timestamp": a['meta']['timestamp'],
                        "origin": "https://duckduckgo.com",
                        "stack": "Error\\nat l (https://duckduckgo.com/dist/wpm.main.f933aba3d6f72c35f872.js:1:358651)\\nat async https://duckduckgo.com/dist/wpm.main.f933aba3d6f72c35f872.js:1:336990",
                        "duration": Math.floor(Math.random() * 10000) + ''
                    }
                }
            ))
        console.log(result)
    }).catch(e => {})
}
"""

def exe_js(code):
    """执行 JavaScript 代码"""
    try:
        p = subprocess.Popen(['node'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except Exception as e:
        p = subprocess.Popen(['nodejs'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(code)
    return stdout.encode().decode().strip()

def get_hash(session):
    """获取 VQD hash"""
    success = False
    while not success:
        try:
            # print("get_hash 开始...")
            
            headers = {
                "Host": "duckduckgo.com",
                "Connection": "keep-alive",
                "sec-ch-ua-platform": "\"Windows\"",
                "Cache-Control": "no-store",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
                "sec-ch-ua-mobile": "?0",
                "x-vqd-accept": "1",
                "Accept": "*/*",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://duckduckgo.com/",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": "dcm=3; dcs=1"
            }
            
            url = 'https://duckduckgo.com/duckchat/v1/status'
            response = session.get(url, headers=headers)
            
            # print("get_hash 响应状态:", response.status_code)
            vqdhash = response.headers['x-vqd-hash-1']
            # print("get_hash 原始 vqdhash:", vqdhash[:30], "...")
            
            # 使用 JavaScript 处理 hash
            vqdhash = exe_js(js_code + "\ndd('" + vqdhash + "')")
            # print("get_hash 处理后:", vqdhash[:30], "...")
            
            if vqdhash != '':
                success = True
                return vqdhash
        except Exception as e:
            print(f"get_hash 错误: {e}")
            time.sleep(5)
            return get_hash(session)


def reload_check():

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
    global cached_models

    return json.dumps(cached_models)



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
        for msg in messages:
            if msg.get("role") == "system":
                msg["role"] = "user"

        # 创建会话
        session = requests.session()
        
        # 重试机制
        max_retries = 10  # 最大重试次数
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print("===================================")
                sndurl = "https://duckduckgo.com/duckchat/v1/chat"
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
                    "canUseTools": True,
                    "canUseApproxLocation": True
                }
                data = json.dumps(data, separators=(',', ':'))
                if debug:
                    print("请求data:", data)
                
                signalsword = {"start": int(time.time()*1000), "events": [{"name": "startNewChat", "delta": 178}, {"name": "recentChatsListImpression", "delta": 282}], "end": 15386}
                
                headers = {
                    "Host": "duckduckgo.com",
                    "Connection": "keep-alive",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "Cache-Control": "no-store",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
                    "sec-ch-ua-mobile": "?0",
                    "x-vqd-accept": "1",
                    "Accept": "*/*",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                    "Referer": "https://duckduckgo.com/",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Cookie": "dcm=3; dcs=1",
                    "content-type": "application/json"
                }
                
                headers['x-fe-signals'] = base64.b64encode(json.dumps(signalsword).encode('utf-8')).decode('utf-8')
                headers['x-vqd-hash-1'] = get_hash(session)
                headers["x-fe-version"] = f"serp_{time.strftime('%Y%m%d', time.localtime())}_{random.randint(100000,999999)}_ET-1518ee4f4ab6fe201b29"
                
                response = session.post(sndurl, headers=headers, data=data)
                response.encoding = 'utf-8'
                
                if response.status_code == 200:
                    if debug:
                        print(f"\033[92m请求成功，状态 {response.status_code}；响应: {response.text[:300]}\033[0m")
                    
                    # 解析响应内容
                    final_content = ""
                    for line in response.iter_lines(decode_unicode=True):
                        if 'data: [DONE]' in line:
                            break
                        elif line.startswith('data: '):
                            data_json = line[6:]
                            try:
                                datax = json.loads(data_json)
                                if 'message' in datax:
                                    final_content += datax['message']
                            except json.JSONDecodeError:
                                continue
                    
                    if debug:
                        print(final_content)
                    return final_content
                else:
                    retry_count += 1
                    if debug:
                        print(f"\033[91m请求失败，状态 {response.status_code}；响应: {response.text[:80]}，第 {retry_count} 次重试\033[0m")
                    
                    if retry_count < max_retries:
                        # 随机等待 0.5-2 秒
                        wait_time = random.uniform(0.5, 2.0)
                        # print(f"等待 {wait_time:.2f} 秒后重试...")
                        time.sleep(wait_time)
                    # else:
                    #     print(f"达到最大重试次数 {max_retries}，停止重试")
                    #     break
                        
            except Exception as retry_e:
                retry_count += 1
                print(f"请求异常: {retry_e}，第 {retry_count} 次重试")
                
                if retry_count < max_retries:
                    # 随机等待 0.5-2 秒
                    wait_time = random.uniform(0.5, 2.0)
                    print(f"等待 {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"达到最大重试次数 {max_retries}，停止重试")
                    break
            
    except Exception as e:
        print(f"chat_completion_messages 使用模型[{model}]发生了异常：", e)
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
    # time1 = time.time() * 1000
    # result_json = get_models()
    # time2 = time.time() * 1000
    # print(f"耗时: {time2 - time1}\r\n获取模型列表:\r\n{result_json}")

    p = "你是谁?你使用的是什么模型?你的知识库截止到什么时间? "
    model_ids = [model['id'] for model in cached_models['data']]
    for id in model_ids:
        mods(id, p)
    # mods("gpt-4o-mini", p)