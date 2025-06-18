# playwright_docker_demo
playwright docker demo


## 环境变量

- **REPLACE_CHAT**: 强制替换目标地址,/开头
- **PREFIX_CHAT**:   支持多个,每个都增加前缀，/开头 
- **APPEND_CHAT**:  增加更多的接口, /开头
- **DEBUG**:  是否debug默认，是否可以查看日志
- **TOKEN**:  是否限制token才能访问，设置则限制，不设置则不限制


## build and test

* build

``` bash
docker build -t ppdemo .
```

* run

``` bash
docker run -d --name ppdemo \
  -p 7860:7860 \
  --shm-size="2g" \
  --cap-add=SYS_ADMIN \
  ppdemo

docker run -d --restart always  --name pekingduck  -p 5009:7860 ghcr.io/hhhaiai/pekingduck:latest

```

* test

``` bash
curl http://localhost:7860/v1/models

curl -X POST http://localhost:7860/api/v1/chat/completions \
  -H 'Accept: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Say this is a test!"}],
    "temperature": 0.7,
    "max_tokens": 150,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }'



curl -X POST http://localhost:7860/api/v1/chat/completions \
  -H 'Accept: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say this is a test!"}],
    "temperature": 0.7,
    "max_tokens": 150,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }'

```