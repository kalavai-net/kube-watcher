# Using https-portal to expose services with SSL certificates

Original library: https://github.com/SteveLTN/https-portal

Example:

```yaml
services:
  https-portal:
    image: steveltn/https-portal:latest
    ports:
      - '80:80'
      - '443:443'
    restart: always
    environment:
      DOMAINS: 'api.cogenai.kalavai.net -> http://51.159.182.127:30379'
      STAGE: 'production' # Don't use production until staging works
      KEEPALIVE_TIMEOUT: 3600
      PROXY_CONNECT_TIMEOUT: 3600
      PROXY_SEND_TIMEOUT: 3600
      PROXY_READ_TIMEOUT: 3600
      CLIENT_MAX_BODY_SIZE: 100M
      # FORCE_RENEW: 'true'
    volumes: 
      - https-portal-data:/var/lib/https-portal

volumes:
  https-portal-data:
```