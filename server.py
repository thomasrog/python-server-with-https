
import argparse
import atexit
import logging
import os
import sys
import inspect
import shutil
from string import Template
from subprocess import call
from version import version

logging.basicConfig(level=logging.INFO)

country = "US"
state = "California"
city = "San Francisco"
organization = "foo bar Company ltd."
organization_unit = "DevOps Dep"
email = "master@foobar-company-ltd.com"
hostname = "localhost"


PY3 = sys.version_info[0] == 3

parser = argparse.ArgumentParser(description='')
parser.add_argument('--host', dest='host', default='localhost')
parser.add_argument('--port', dest='port', type=int, default=4443)
args = parser.parse_args()

server_host = args.host
server_port = args.port


user_desktop_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
logging.info(user_desktop_path)

certs_path = user_desktop_path + '/certs/'

if os.path.exists(certs_path):
    shutil.rmtree(certs_path)

os.makedirs(certs_path)


ssl_cert_path = certs_path + hostname + '.crt'
ssl_key_path = certs_path + hostname + '.key'
ssl_server_key_crt_path = certs_path + '/server.pem'
config_out_path = certs_path + hostname + '.cnf'

if PY3:
    OpenSslExecutableNotFoundError = FileNotFoundError
else:
    OpenSslExecutableNotFoundError = OSError

def create_ssl_config_file() :
    template_path = user_desktop_path + '/openssl-template.cnf'
    filein = open( template_path )
    src = Template( filein.read() )

    d={ 'country':country, 'state':state, 'city':city,
        'organization':organization,'organization_unit':organization_unit,
        'email':email,'hostname':hostname}

    result = src.substitute(d)
    with open(config_out_path, 'a') as the_file:
        the_file.write(result)

def create_ssl_cert():
    
    if PY3:
        from subprocess import DEVNULL
    else:
        DEVNULL = open(os.devnull, 'wb')

    try:
        ssl_exec_list = ['C:/OpenSSL-Win32/bin/openssl', 'req', '-new', '-x509','-newkey', 'rsa:2048', '-keyout', ssl_key_path,
                         '-out', ssl_cert_path, '-days', '365', '-nodes', '-config', config_out_path]
        call(ssl_exec_list, stdout=DEVNULL, stderr=DEVNULL)
    except OpenSslExecutableNotFoundError:
        logging.error('openssl executable not found!')
        exit(1)

    logging.info('Self signed ssl certificate created at {}'.format(ssl_cert_path))

def merge_cert_and_privatekey_to_server_pem():
    filenames = [ssl_cert_path, ssl_key_path]
    with open(ssl_server_key_crt_path, 'w') as outfile:
        for fname in filenames:
            with open(fname) as infile:
                outfile.write(infile.read())

def exit_handler():
    #os.remove(ssl_cert_path)
    logging.info('Bye!')


def main():
    logging.info('pyhttps {}'.format(version))
    create_ssl_config_file()
    create_ssl_cert()
    merge_cert_and_privatekey_to_server_pem()
    atexit.register(exit_handler)

    if PY3:
        import http.server
        import socketserver
        import ssl

        logging.info('Server running... https://{}:{}'.format(server_host, server_port))
        httpd = socketserver.TCPServer((server_host, server_port), http.server.SimpleHTTPRequestHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=ssl_server_key_crt_path, server_side=True)
    else:
        import BaseHTTPServer
        import SimpleHTTPServer
        import ssl

        logging.info('Server running... https://{}:{}'.format(server_host, server_port))
        httpd = BaseHTTPServer.HTTPServer((server_host, server_port), SimpleHTTPServer.SimpleHTTPRequestHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=ssl_server_key_crt_path, server_side=True)

    httpd.serve_forever()
    
main()
