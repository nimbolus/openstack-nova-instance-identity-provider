import signal

from oslo_config import cfg
from waitress import serve as waitress_serve
from flask import Flask, request, jsonify
from keystonemiddleware import auth_token
from openstack import connection as os_conn
from oidc import OIDCProvider


CONF = cfg.CONF

common_opts = [
    cfg.StrOpt('listen_host', default="0.0.0.0",
               help="Host the service listens to"),
    cfg.IntOpt('listen_port', default=8001,
               help="Port the service listens to"),
    cfg.BoolOpt('project_name_lookup', default=False,
                help="Lookup project name and add corresponding token claim"),
]

CONF.register_opts(common_opts)

oidc_provider_opts = [
    cfg.StrOpt('issuer_url', default="https://idp.example.com",
               help="URL of the OIDC issuer of the generated tokens"),
    cfg.StrOpt('audience', default="openstack",
               help="OIDC audience of generated tokens"),
    cfg.StrOpt('signing_algorithm', default="ES256",
               help="JWT signing algorithm"),
    cfg.StrOpt('jwks_state', default="jwks.json",
               help="JWKS state file for persisting public keys"),
    cfg.IntOpt('key_rotation_period', default=24,
               help="Rotation period for the signing key in hours"),
    cfg.IntOpt('token_lifetime', default=1,
               help="Lifetime of generated tokens in hours"),
]

oidc_provider_config = cfg.OptGroup(
    name='oidc_provider', title="OIDC Provider Options")
CONF.register_group(oidc_provider_config)
CONF.register_opts(oidc_provider_opts, group=oidc_provider_config)
config_file = 'nova-instance-identity.conf'
CONF(default_config_files=[config_file])


def wrap_keystone_middleware(app):
    """Keystone middleware wrapper for paths which require authentication"""

    # Paths which bypass Keystone authentication
    paths_to_exclude = ['/.well-known']

    class AuthMiddlewareWrapper:
        def __init__(self, app):
            self.app = app
            self.keystone_middleware = auth_token.AuthProtocol(self.app, {})

        def __call__(self, environ, start_response):
            # If current path starts with a string defined in excluded path list, skip Keystone authentication
            if any(environ['PATH_INFO'].startswith(path) for path in paths_to_exclude):
                return self.app(environ, start_response)
            # Enforce Keystone authentication
            return self.keystone_middleware(environ, start_response)

    return AuthMiddlewareWrapper(app)


app = Flask(__name__)
app.wsgi_app = wrap_keystone_middleware(app.wsgi_app)

oidc_provider = OIDCProvider(app, CONF.oidc_provider)

os_client_auth_args = {
    'auth_url': CONF.keystone_authtoken.auth_url,
    'project_domain_id': CONF.keystone_authtoken.project_domain_id,
    'user_domain_id': CONF.keystone_authtoken.user_domain_id,
    'username': CONF.keystone_authtoken.username,
    'password': CONF.keystone_authtoken.password,
    'project_name': CONF.keystone_authtoken.project_name,
}
os_client = os_conn.Connection(**os_client_auth_args)


@app.route('/vendordata/instance-identity', methods=['POST'])
def vendordata():
    """Create response to Nova vendordata request with instance identity token"""
    data = request.get_json()
    payload = {
        'instance-id': data['instance-id'],
        'project-id': data['project-id'],
        'image-id': data['image-id'],
        'hostname': data['hostname'],
        'metadata': data['metadata'],
    }

    if CONF.project_name_lookup:
        project = os_client.get_project(data['project-id'])
        payload['project-name'] = project.name

    if 'assume-role' in data['metadata']:
        payload['assume-role'] = data['metadata']['assume-role']

    token, expires_at = oidc_provider.create_token(
        data['instance-id'], payload)

    return jsonify({
        'token': token,
        'expires_at': expires_at,
    })


def handle_sigterm(signum, frame):
    raise KeyboardInterrupt()


if __name__ == '__main__':
    # waitress does not listen to SIGTERM, so raise SIGINT
    signal.signal(signal.SIGTERM, handle_sigterm)

    print(f"Starting server on {CONF.listen_host}:{CONF.listen_port}")
    waitress_serve(app, host=CONF.listen_host, port=CONF.listen_port)
