"""Provision a local PostgreSQL instance and start Birge on Windows."""

import argparse
from base64 import b64decode
import hashlib
import msvcrt
import os
from pathlib import Path
from secrets import token_hex
import socket
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

from dotenv import dotenv_values
import psycopg
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.birge-local'
HOST = '127.0.0.1'
PG_PORT = 55432
APP_PORT = 8000
PG_PACKAGE = '18.4.0-beta.17'
PG_URL = f'https://registry.npmjs.org/@embedded-postgres/windows-x64/-/windows-x64-{PG_PACKAGE}.tgz'
PG_SHA512 = b64decode(
    'AwRerliA4IGWyW5jWBvHt5vidVUSB0QQW9Tt2y7ScnmifnCb/awfxZr4BkBSTv+gNt8Djcddqs+xSF5Z6/CkTg=='
)


def postgres_bin():
    install = STATE / f'postgres-{PG_PACKAGE}'
    binaries = install / 'bin'
    if (binaries / 'postgres.exe').is_file():
        return binaries

    print('Downloading local PostgreSQL for Windows x64...', flush=True)
    try:
        with urlopen(PG_URL, timeout=60) as response:
            archive = response.read()
    except (OSError, URLError) as error:
        raise RuntimeError('Could not download PostgreSQL. Check internet access and retry.') from error
    if hashlib.sha512(archive).digest() != PG_SHA512:
        raise RuntimeError('PostgreSQL download failed checksum verification.')

    with TemporaryDirectory(dir=STATE) as workdir:
        temporary = Path(workdir)
        bundle = temporary / 'postgres.tgz'
        bundle.write_bytes(archive)
        with tarfile.open(bundle) as package:
            package.extractall(
                temporary, members=(entry for entry in package if entry.name.startswith('package/native/')),
                filter='data',
            )
        (temporary / 'package' / 'native').rename(install)
    return binaries


def database_ready(password):
    try:
        with psycopg.connect(
            host=HOST, port=PG_PORT, dbname='postgres', user='birge',
            password=password, connect_timeout=2,
        ):
            return True
    except psycopg.OperationalError:
        return False


def start_postgres():
    binaries = postgres_bin()
    data = STATE / 'data'
    password_file = STATE / 'password.txt'
    if not password_file.exists():
        if (data / 'PG_VERSION').exists():
            raise RuntimeError(f'Restore the local database password file at {password_file}.')
        password_file.write_text(token_hex(32) + '\n', encoding='ascii')
    password = password_file.read_text(encoding='ascii').strip()
    if not (data / 'PG_VERSION').exists():
        print('Initializing the local PostgreSQL database...', flush=True)
        result = subprocess.run([
            str(binaries / 'initdb.exe'), '-D', str(data), '-U', 'birge',
            '--auth=scram-sha-256', f'--pwfile={password_file}', '--encoding=UTF8', '--no-locale',
        ], creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True)
        if result.returncode:
            sys.stderr.buffer.write(result.stdout + result.stderr)
            raise RuntimeError('Could not initialize PostgreSQL. See the initdb output above.')

    if not database_ready(password):
        logfile = STATE / 'postgres.log'
        with logfile.open('ab') as log:
            process = subprocess.Popen(
                [str(binaries / 'postgres.exe'), '-D', str(data), '-h', HOST, '-p', str(PG_PORT)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                # PostgreSQL workers inherit this windowless console from the server.
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        deadline = time.monotonic() + 45
        while not database_ready(password):
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError(f'PostgreSQL did not start on port {PG_PORT}. See {logfile}.')
            time.sleep(0.5)

    return f'postgresql+psycopg://birge:{password}@{HOST}:{PG_PORT}/postgres'


def configure_database():
    if os.getenv('DATABASE_URL') or dotenv_values(ROOT / '.env').get('DATABASE_URL'):
        return

    STATE.mkdir(exist_ok=True)
    with (STATE / 'startup.lock').open('ab') as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('Another window is setting up the local database. Try again shortly.') from error
        os.environ['DATABASE_URL'] = start_postgres()


def open_when_ready(server, url):
    while not server.started and not server.should_exit:
        time.sleep(0.1)
    if server.started:
        webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true', help='Start without opening a browser.')
    args = parser.parse_args()

    try:
        configure_database()
        print('Applying database migrations...', flush=True)
        migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT)
        if migration.returncode:
            raise RuntimeError('Database migrations failed. Check the connection and the output above.')
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                listener.bind((HOST, APP_PORT))
            except OSError as error:
                if error.winerror not in {10013, 10048}:  # Reserved or already in use on Windows.
                    raise
                listener.bind((HOST, 0))
            port = listener.getsockname()[1]
            url = f'http://{HOST}:{port}'
            server = uvicorn.Server(uvicorn.Config('app.main:app', host=HOST, port=port))
            print(f'Birge: {url}/app/   Swagger: {url}/docs', flush=True)
            if not args.no_browser:
                Thread(target=open_when_ready, args=(server, f'{url}/app/'), daemon=True).start()
            server.run(sockets=[listener])
        return 0 if server.started else 1
    except (OSError, RuntimeError, tarfile.TarError) as error:
        print(f'BIRGE: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
