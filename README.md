# splitwise-demos
This repo contains a set of demos for Splitwise.

## Architecture

```
                 +-----------+                     +------------------+            +-----------+
                 |           |                     |                  |            |           |
                 |           |                     |  +------------+  |            |           |
                 |           |                     |  |  GPU HBM   |  |            |           |
                 |           | /chat/completions   |  +-+----------+  |            |           |
                 |           +<------------------->+    |             |  Put       |           |
                 |           | set max_tokens=1    |    |GPUConnector +----------->+           |
                 |           |                     |    v             |  TCP/RDMA  |           |
                 |           |                     |  +-+----------+  |            |           |
                 |           |                     |  |  CPU DRAM  |  |            |           |
                 |           |                     |  +------------+  |            |           |
                 |           |                     |                  |            |           |
                 |           |                     |      Prefill     |            |           |
                 |           |                     +------------------+            |           |
/chat/completions|           |                                                     |  KV Cache |
+--------------->+   Proxy   |                                                     |  Storage  |
 max_tokens=100  |           |                                                     |  Backend  |
                 |           |                     +------------------+            |           |
                 |           |                     |                  |            |           |
                 |           |                     |  +------------+  |            |           |
                 |           |                     |  |  GPU HBM   |  |            |           |
                 |           |                     |  +-+----------+  |            |           |
                 |           | /chat/completions   |    |             |            |           |
                 |           +<------------------->+    |GPUConnector |            |           |
                 |           | set max_tokens=100  |    v             |            |           |
                 |           |                     |  +-+----------+  |  Get       |           |
                 |           |                     |  |  CPU DRAM  |  +----------->+           |
                 |           |                     |  +------------+  |  TCP/RDMA  |           |
                 |           |                     |                  |            |           |
                 |           |                     |      Decode      |            |           |
                 +-----------+                     +------------------+            +-----------+
```

## Installation


## Usage

### Configurations

``` yaml
# example.yaml
chunk_size: 32
local_device: "cpu"
remote_url: "lm://192.168.0.1:10080"
remote_serde: "naive" # naive, kivi, cachegen, choose naive avoid (de)serialization
max_local_cpu_size: 20 # GB

# Whether retrieve() is pipelined or not
pipelined_backend: False
```

### Start the LMSLocalBackend
```bash
docker run -d -p 10080:8000 ghcr.io/bd-iaas-us/lmcache-lmslocalbackend:latest 0.0.0.0 8000 "cpu"
```

### Start the Prefill

```bash
docker run -d -p 8010:8000 --gpus="device=0" -v ./example.yaml:/app/example.yaml -v ./DeepSeek-V2-Lite:/app/DeepSeek-V2-Lite --env "VLLM_MLA_DISABLE=1" --env "LMCACHE_CONFIG_FILE=/app/example.yaml" --env "LMCACHE_USE_EXPERIMENTAL=True" ghcr.io/bd-iaas-us/vllm-lmcache:latest /app/DeepSeek-V2-Lite --port 8000 --max-model-len 8192 --trust-remote-code --enforce-eager --gpu-memory-utilization 0.9 --swap-space 0 --kv-transfer-config '{"kv_connector":"LMCacheConnector","kv_role":"kv_producer"}'
```

### Start the Decode

```bash
docker run -d -p 8020:8000 --gpus="device=1" -v ./example.yaml:/app/example.yaml -v ./DeepSeek-V2-Lite:/app/DeepSeek-V2-Lite --env "VLLM_MLA_DISABLE=1" --env "LMCACHE_CONFIG_FILE=/app/example.yaml" --env "LMCACHE_USE_EXPERIMENTAL=True" ghcr.io/bd-iaas-us/vllm-lmcache:latest /app/DeepSeek-V2-Lite --port 8000 --max-model-len 8192 --trust-remote-code --enforce-eager --gpu-memory-utilization 0.9 --swap-space 0 --kv-transfer-config '{"kv_connector":"LMCacheConnector","kv_role":"kv_consumer"}'
```

### Start the KvProxy
#### Option 1


```bash
docker run -p 8030:8000 --env "PREFILL_ENDPOINTS=http://192.168.0.1:8010" --env "DECODE_ENDPOINTS=http://192.168.0.1:8020" ghcr.io/bd-iaas-us/kvproxy:latest --host 0.0.0.0 --port 8000
```

#### Option 2
``` bash
# .env file
PREFILL_ENDPOINTS=http://192.168.0.1:8010
DECODE_ENDPOINTS=http://192.168.0.1:8020
```

```bash
docker run -p 8030:8000 -v ./.env:/app/.env pull ghcr.io/bd-iaas-us/kvproxy:latest --host 0.0.0.0 --port 8000
```

### Sample Request
```bash
curl http://127.0.0.1:8030/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "/app/DeepSeek-V2-Lite", "temperature": 0.75, "messages": [ {"role": "user", "content": "San Francisco"}], "max_tokens": 200}'
curl http://127.0.0.1:8030/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "/app/DeepSeek-V2-Lite", "temperature": 0.75, "messages": [ {"role": "user", "content": "San Francisco is a major city in California, United States, known for its iconic landmarks, cultural diversity, and technological innovation. Key features include:\n\n1. **Golden Gate Bridge**: A famous red suspension bridge and symbol of the city.\n2. **Alcatraz Island**: A former federal prison located in San Francisco "}], "max_tokens": 200}'
```

## Appendix