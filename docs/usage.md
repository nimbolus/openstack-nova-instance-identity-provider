# Usage

## OIDC Provider

To authenticate against other OIDC providers, the Nova Instance Identity Provider needs to be registered as a trusted token issuer on the OIDC provider side. The required information can be found below:

**Issuer url:** defined in config file
**Audience:** defined in config file
**OIDC discovery url path:** `/.well-known/openid-configuration`
**JWKS url path:** `/.well-known/jwks.json`

## Use with OpenStack CLI

To use the Nova Instance Identity Provider in combination with the OpenStack CLI, the following environment variables needs to be set:

```sh
export OS_AUTH_URL="https://keystone.example.com/v3"
export OS_AUTH_TYPE="v3oidcaccesstoken"
export OS_PROTOCOL="openid"
export OS_IDENTITY_PROVIDER="nova-instance-identity"
export OS_IDENTITY_API_VERSION="3"
export OS_PROJECT_ID="$(curl -s http://169.254.169.254/openstack/latest/meta_data.json | jq -r '.project_id')"
export OS_ACCESS_TOKEN="$(curl -s http://169.254.169.254/openstack/latest/vendor_data2.json | jq -r '.instance_identity.token')"
```
