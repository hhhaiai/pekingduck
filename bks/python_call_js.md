

``` python
import execjs


js_code = """
 js code
"""
ctx = execjs.compile(js_code)
调用具体方法
hash_result = ctx.call("hash", x_vqd_hash)
```