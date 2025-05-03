# Identity Provider for OpenStack Nova Instances

A OIDC identity provider which issues tokens for OpenStack compute instances using the [vendordata](https://docs.openstack.org/nova/latest/user/metadata.html#vendordata) approach.

> :warning: **Disclaimer**: This code is in an early development state and not tested extensively for bugs and security issues. If you find some, please raise an issue or merge request.

## What does it do?

The instance identity provider issues JWT tokens containing the metadata information of the compute instance it is called from. Further, it offers an JWKS endpoint which can be called by other identity providers to verify the token validity. This enables compute instance to request a token using the Nova metadata API and authenticate to other OIDC providers (like e.g. Keystone) which trust the Nova identity provider.

## How does it work?

OpenStack allows operators to extend the Nova metadata API using custom [vendordata](https://docs.openstack.org/nova/latest/user/metadata.html#vendordata) services. If this vendordata API endpoint is called by a compute instance, Nova enriches the request with the metadata (instance ID, project ID, hostname, user-provided properties) of the instance and forwards the request to the custom vendordata service, like this identity provider.

The Nova instance identity provider packs the instance information into a JWT token and signs it with its private key. This token is then returned to the compute instance, where it can be used to authenticate against other OIDC providers then which fetch the public key from the instance identity provider to verify the token validity.

An example of such an OIDC provider could be Keystone using the [OIDC access token flow](https://docs.openstack.org/keystoneauth/latest/plugin-options.html#v3oidcaccesstoken), where the JWT token can be exchanged for a Keystone token based on mappings using the instance metadata properties (see [Keystone Federation](https://docs.openstack.org/keystone/latest/admin/federation/introduction.html)).

![Nova instance identity provider](./docs/images/nova-instance-identity-provider.svg)
