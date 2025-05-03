# Installation

1. Create config file based on [nova-instance-identity.sample.conf](../dist/nova-instance-identity.sample.conf):

```sh
mkdir /etc/nova-instance-identity
touch /etc/nova-instance-identity/nova-instance-identity.conf
```

2. Start container:

```sh
podman run -d --name nova_instance_identity --net host \
    -v nova_instance_identity_data:/app/data:rw \
    -v /etc/nova-instance-identity/nova-instance-identity.conf:/app/nova-instance-identity.conf:ro \
    ghcr.io/nimbolus/openstack-nova-instance-identity-provider
```

3. If using [kolla-ansible](https://docs.openstack.org/kolla-ansible/latest/), optionally create a haproxy config based on [haproxy.sample.cfg](../dist/haproxy.sample.cfg) at `/etc/kolla/config/haproxy/services.d/nova-instance-identity.cfg` on your deployment host and rollout haproxy role.

4. Register the vendordata endpoint in `nova.conf`, e.g. with kolla-ansible add the following config to `/etc/kolla/config/nova.conf` on your deployment host and rollout nova role.

```
[api]
vendordata_providers = DynamicJSON
vendordata_dynamic_targets = instance_identity@https://{{ kolla_internal_vip_address }}:8001/vendordata/instance-identity

[vendordata_dynamic_auth]
auth_type = password
auth_url = https://{{ kolla_internal_fqdn }}:5000
project_domain_id = default
user_domain_id = default
project_name = service
username = nova
password = {{ nova_keystone_password }}
```
