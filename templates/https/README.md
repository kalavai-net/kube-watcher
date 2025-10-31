# Using https-portal to expose services with SSL certificates

Original library: https://github.com/SteveLTN/https-portal

## Manual deployment (docker compose)

Make sure you copy the default.ssl.conf.erb file to the root folder of where you are deploying https.

Then, create a yaml file as below. Example:

```yaml
services:
  https-portal:
    image: steveltn/https-portal:latest
    ports:
      - '80:80'
      - '443:443'
    restart: always
    environment:
      DOMAINS: 'api.cogenai.kalavai.net -> http://51.159.161.139:31851, demo1.kalavai.net -> http://51.159.161.139:32111, demo2.kalavai.net -> http://51.159.161.139:32222'
      STAGE: 'production' # Don't use production until staging works
      KEEPALIVE_TIMEOUT: 3600
      PROXY_CONNECT_TIMEOUT: 3600
      PROXY_SEND_TIMEOUT: 3600
      PROXY_READ_TIMEOUT: 3600
      CLIENT_MAX_BODY_SIZE: 100M
      # FORCE_RENEW: 'true'
    volumes: 
      - https-portal-data:/var/lib/https-portal
      - ./default.ssl.conf.erb:/var/lib/nginx-conf/default.ssl.conf.erb:ro

volumes:
  https-portal-data:
```

Then start the service:
```bash
docker compose -f https.yaml up -d
```

