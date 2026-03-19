# Monetise GPUs without demand

Become a host on Akash: https://akash.network/docs/providers/setup-and-installation/kubespray/

## Configuration

Install akash CLI

GLIBC_2.38 is required (ubuntu +24), use the below in docker:

```bash
docker run -it --rm ubuntu:24.04
```

Inside the container:

```bash
# Install dependencies
cd ~
apt update && apt install jq unzip curl nano -y

# Download and install provider-services
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | bash

# add to /etc/environment PATH
nano /etc/environment
PAT="XXX:/root/bin"

. /etc/environment

# Create account
AKASH_KEY_NAME=kalavai-akash
AKASH_KEYRING_BACKEND=os
provider-services keys add $AKASH_KEY_NAME
export AKASH_ACCOUNT_ADDRESS="$(provider-services keys show $AKASH_KEY_NAME -a)"
echo $AKASH_ACCOUNT_ADDRESS
```

Store `$AKASH_ACCOUNT_ADDRESS` somewhere safe

# Fund wallet

1. Transfer (withdraw from Kraken) to account address
2. Check balance


AKASH_NET="https://raw.githubusercontent.com/akash-network/net/main/mainnet"
AKASH_VERSION="$(curl -s https://api.github.com/repos/akash-network/provider/releases/latest | jq -r '.tag_name')"
export AKASH_CHAIN_ID="$(curl -s "$AKASH_NET/chain-id.txt")"
export AKASH_NODE="$(curl -s "$AKASH_NET/rpc-nodes.txt" | shuf -n 1)"
provider-services query bank balances --node $AKASH_NODE $AKASH_ACCOUNT_ADDRESS

Export wallet key

```bash
provider-services keys export $AKASH_KEY_NAME > key.pem
echo "KalavaiAkash" > key-pass.txt
```

Encode secrets:
```bash
KEY_SECRET=$(cat /root/provider/key.pem | openssl base64 -A)
KEY_PASSWORD=$(cat /root/provider/key-pass.txt | openssl base64 -A)
ACCOUNT_ADDRESS=$AKASH_ACCOUNT_ADDRESS
```

# Install in kubernetes

```bash
helm repo add akash https://akash-network.github.io/helm-charts
helm repo update
```

Create namespaces
```bash
kubectl create namespace akash-services
kubectl create namespace lease
kubectl label namespace akash-services akash.network=true
kubectl label namespace lease akash.network=true
```

