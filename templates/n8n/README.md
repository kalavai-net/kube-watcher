# n8n automation workflows

A template to deploy a full n8n server + UI to edit, deploy and manage workflows.


Authentication:

If the webhook input has authentication enabled (can be done within the Webhook node), then you must pass it in the request. For instance, using Header auth:

```bash
{<auth key name>: <auth key value>}
```

## Swagger API

Available at 
```bash
<endpoint>/api/v1/docs
# E.g.: http://localhost:31684/api/v1/docs
```

More info: https://docs.n8n.io/api/using-api-playground/

Swagger API requires global API KEY authentication, which can be generated within the GUI (Settings). Then pass as a header to the request:

```bash
{"X-N8N-API-KEY": <api key>}
```