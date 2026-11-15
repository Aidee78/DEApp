# Zoho Mail setup

## OAuth app

Register the OAuth client in the Zoho API Console. Use the data center that
matches the target Zoho account. Configure the corresponding accounts server
and Mail API base URL in the local `.env` file.

DEApp only needs read access to messages. The requested Mail scope is:

```text
ZohoMail.messages.READ