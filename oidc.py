import jwt
import base64
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization


class OIDCProvider:
    def __init__(self, app, conf):
        self.conf = conf
        self.private_key = self.load_private_key()
        self.public_key = self.load_public_key()
        self.app = app
        self.setup_routes()

    def load_private_key(self):
        """Load private key from file"""
        with open(self.conf.private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
        return private_key

    def load_public_key(self):
        """Load public key from file"""
        with open(self.conf.public_key_path, 'rb') as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read()
            )
        return public_key

    def setup_routes(self):
        # TODO: This route is not tested yet and only a dummy for implementing a openid discovery endpoint
        @self.app.route('/.well-known/openid-configuration')
        def openid_configuration():
            return {
                'issuer': self.conf.issuer_url,
                'jwks_uri': f"{self.conf.issuer_url}/.well-known/jwks.json",
                'response_types_supported': ['id_token'],
                'subject_types_supported': ['public'],
                'id_token_signing_alg_values_supported': ['RS256'],
                'scopes_supported': ['openid', 'profile', 'email'],
                'claims_supported': ['sub', 'iss', 'aud', 'exp', 'iat']
            }

        @self.app.route('/.well-known/jwks.json')
        def jwks():
            public_numbers = self.public_key.public_numbers()
            return {
                'keys': [
                    {
                        'kty': 'RSA',
                        'use': 'sig',
                        'kid': '1',
                        'n': self.int_to_base64(public_numbers.n),
                        'e': self.int_to_base64(public_numbers.e),
                        'alg': 'RS256'
                    }
                ]
            }

    def int_to_base64(self, value):
        """Convert an integer to a Base64URL-encoded string"""
        value_hex = format(value, 'x')
        # Ensure even length
        if len(value_hex) % 2 == 1:
            value_hex = '0' + value_hex
        value_bytes = bytes.fromhex(value_hex)
        return base64.urlsafe_b64encode(value_bytes).rstrip(b'=').decode('ascii')

    def create_token(self, sub, metadata):
        """Generate a new token with given subject and metadata attributes"""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.conf.token_lifetime)
        payload = {
            'iss': self.conf.issuer_url,
            'sub': sub,
            'aud': self.conf.audience,
            'iat': now,
            'exp': expires_at,
        }

        return jwt.encode(payload | metadata, self.private_key, algorithm='RS256'), expires_at
