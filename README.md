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


## Appendix