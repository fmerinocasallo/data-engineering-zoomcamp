from base64 import standard_b64encode
from hashlib import pbkdf2_hmac, sha256
import hmac
from os import urandom
import sys
from typing import Optional

import click


SALT_SIZE = 16
DIGEST_LEN = 32
ITERATIONS = 4096


def b64enc(b: bytes) -> str:
    return standard_b64encode(b).decode('utf8')


@click.command()
@click.option("-p", "--password", help='Password.')
@click.option("-i", "--input_file", help='Input file storing the password.')
def pg_scram_sha256(password: Optional[str], input_file: Optional[str]) -> str:
    if (not password) and (not input_file):
        print_help()

        return None
    else:
        if password:
            passwd = password
        else:
            with open(input_file, 'r') as f:
                passwd = f.readline().strip()

    salt = urandom(SALT_SIZE)
    digest_key = pbkdf2_hmac(
        'sha256',
        passwd.encode('utf8'),
        salt,
        ITERATIONS,
        DIGEST_LEN,
    )
    client_key = hmac.digest(
        digest_key,
        'Client Key'.encode('utf8'),
        'sha256',
    )
    stored_key = sha256(client_key).digest()
    server_key = hmac.digest(
        digest_key,
        'Server Key'.encode('utf8'),
        'sha256',
    )
    return (
        f'SCRAM-SHA-256${ITERATIONS}:{b64enc(salt)}'
        f'${b64enc(stored_key)}:{b64enc(server_key)}'
    )


def print_help():
    with click.get_current_context() as ctx:
        click.echo(ctx.get_help())
        ctx.exit()


def main():
    encrypted_passwd = pg_scram_sha256(standalone_mode=False)

    if encrypted_passwd:
        print(f"encrypted passwd: {encrypted_passwd}")


if __name__ == "__main__":
    main()
