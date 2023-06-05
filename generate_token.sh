ACCOUNT_NAME="kalavai-admin"

kubectl create serviceaccount $ACCOUNT_NAME
kubectl create clusterrolebinding admin-user-binding --clusterrole cluster-admin --serviceaccount default:$ACCOUNT_NAME
kubectl create token $ACCOUNT_NAME