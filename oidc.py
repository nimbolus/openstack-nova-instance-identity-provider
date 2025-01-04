import os
import jwt
import base64
import uuid
import json
import schedule

from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from threading import Lock


class OIDCProvider:
    SUPPORTED_SIGNING_ALGORITHMS = ["RS256", 'RS384', 'RS512',
                                    'ES256', 'ES384', 'ES512']
    SIGNING_ALGORITHM_CURVE = {ec.SECP256R1: "P-256",
                               ec.SECP384R1: "P-384",
                               ec.SECP521R1: "P-521", }

    def __init__(self, app, conf):
        self.conf = conf
        self.mutex = Lock()
        self.jwks_keys = list()
        self.load_jwks_state()
        self.generate_private_key()
        self.app = app
        self.setup_routes()
        self.scheduler = schedule.Scheduler()
        self.scheduler.every(self.conf.key_rotation_period).hours.do(
            self.generate_private_key)

    def load_jwks_state(self):
        """Load JWKS keys cfrom state file"""
        self.mutex.acquire()
        if os.path.exists(self.conf.jwks_state):
            with open(self.conf.jwks_state, 'rb') as state:
                self.jwks_keys = json.load(state)
        self.mutex.release()

    def generate_private_key(self):
        """Generate private key for signing tokens"""
        algo = self.conf.signing_algorithm
        if algo == 'RS256':
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048)
        elif algo == 'RS384':
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=3072)
        elif algo == 'RS512':
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=4096)
        elif algo == 'ES256':
            private_key = ec.generate_private_key(ec.SECP256R1())
        elif algo == 'ES384':
            private_key = ec.generate_private_key(ec.SECP384R1())
        elif algo == 'ES512':
            private_key = ec.generate_private_key(ec.SECP521R1())
        else:
            raise ValueError(f"Unsupported key type, supported are {
                             self.SUPPORTED_SIGNING_ALGORITHMS}")

        public_numbers = private_key.public_key().public_numbers()
        if isinstance(private_key, rsa.RSAPrivateKey):
            jwks_key = {
                'kty': 'RSA',
                'use': 'sig',
                'kid': uuid.uuid4(),
                'n': self.int_to_base64(public_numbers.n),
                'e': self.int_to_base64(public_numbers.e),
                'alg': self.conf.signing_algorithm,
            }
        elif isinstance(private_key, ec.EllipticCurvePrivateKey):
            jwks_key = {
                'kty': 'EC',
                'crv': self.SIGNING_ALGORITHM_CURVE.get(type(private_key)),
                'use': 'sig',
                'kid': str(uuid.uuid4()),
                'x': self.int_to_base64(public_numbers.x),
                'y': self.int_to_base64(public_numbers.y),
                'alg': self.conf.signing_algorithm,
            }
        else:
            raise TypeError("Unsupported private key type")

        self.mutex.acquire()

        self.private_key = private_key
        self.jwks_keys.append(jwks_key)

        # remove old public keys from JWKS
        if len(self.jwks_keys) > 3:
            self.jwks_keys.pop(0)

        # persist jwks state
        with open(self.conf.jwks_state, 'w') as state:
            json.dump(self.jwks_keys, state)

        self.mutex.release()

    def setup_routes(self):
        @self.app.route('/.well-known/openid-configuration')
        def openid_configuration():
            return {
                'issuer': self.conf.issuer_url,
                'jwks_uri': f"{self.conf.issuer_url}/.well-known/jwks.json",
                'response_types_supported': ['id_token'],
                'subject_types_supported': ['public'],
                'id_token_signing_alg_values_supported': self.SUPPORTED_SIGNING_ALGORITHMS,
            }

        @self.app.route('/.well-known/jwks.json')
        def jwks():
            return {'keys': self.jwks_keys}

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
        self.scheduler.run_pending()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.conf.token_lifetime)
        payload = {
            'iss': self.conf.issuer_url,
            'sub': sub,
            'aud': self.conf.audience,
            'iat': now,
            'exp': expires_at,
        }

        self.mutex.acquire()
        token = jwt.encode(payload | metadata, self.private_key,
                           algorithm=self.conf.signing_algorithm)
        self.mutex.release()
        return token, expires_at
