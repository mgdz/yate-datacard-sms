#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import uuid
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.protocols.basic import LineReceiver
from config import YATE_HOST, YATE_PORT


def escape(string):
    esc_string = ''
    for c in string:
        if c == "%" or c == ":" or ord(c) < 32:
            esc_string += "%"+chr(ord(c) + 64)
        else:
            esc_string += c
    return esc_string


def unescape(string):
    unesc_string = ''
    i = 0
    while i < len(string):
        c = string[i]
        if c == "%":
            i += 1
            c = chr(ord(string[i]) - 64)
        i += 1
        unesc_string += c
    return unesc_string


class ExtModuleProtocol(LineReceiver):

    delimiter = "\n"
    
    def sendMessage(self, message):
        # print("sendng message: %s" % message)
        self.transport.write(message)
        self.transport.write("\n")

    def enqueue(self, message_name, retvalue, **kwargs):
        # print("Enqueueing message '%s' with params: '%s'" % (message_name, kwargs))
        params = []
        for key, value in kwargs.items():
            if value:
                params.append(escape("%s=%s" % (key, value)))
            else:
                params.append(escape("%s" % key))

        message_id = uuid.uuid4().hex

        message = "%%%%>message:%(id)s:%(time)s:%(name)s:%(retvalue)s:%(params)s" % {
            "id": message_id,
            "time": int(time.time()),
            "name": escape(message_name),
            "retvalue": escape(retvalue),
            "params": ":".join(params)
            }

        self.sendMessage(message)
        return message_id

    def connectionMade(self):
        self.sendMessage("%%>connect:global\n")
        self.install_handler('datacard.sms', 100)

    def install_handler(self, message, priority=100, filter_name=None, filter_value=None):
        # %%>install
        install_msg = "%%%%>install:%s:%s" % (priority, escape(message))
        if filter_name:
            install_msg = "%s:%s" % (install_msg, escape(filter_name))
            if filter_value:
                install_msg = "%s:%s" % (install_msg, escape(filter_value))
        self.sendMessage(install_msg)

    def answer(self, message_id, message_name, processed, retvalue, payload):
        # print("Answering to server request")
        params = []
        for key, value in payload.items():
            if value:
                params.append(escape("%s=%s" % (key, value)))
            else:
                params.append(escape("%s" % key))

        message = "%%%%<message:%(id)s:%(processed)s:%(name)s:%(retvalue)s:%(params)s" % {
            "id": escape(message_id),
            "processed": processed and "true" or "false",
            "name": escape(message_name),
            "retvalue": escape(retvalue),
            "params": ":".join(params)
            }

        self.sendMessage(message)
        
    def process_request(self, request):
        # print("Request received: %s" % request)
        data = request.split(":")
        data = [unescape(d) for d in data]
        # print("Data: %s. Processing message" % data)
        if data[0] == "message":
            message_id = data[1]
            message_name = data[3]
            message_data = dict(d.split("=") for d in data[5:])
            # print("Message data: %s" % message_data)
            # print("Message ID: %s Name: %s" % (message_id, message_name))
            print("Incoming message from %s. Text: %s" % (message_data['caller'], message_data['text']))


        self.answer(message_id, message_name, False, "", {})

    def process_response(self, response):
        print("Recieved response: %s" % response) 
        data = response.split(":")
        data = [unescape(d) for d in data]
        msg_name = data.pop(0)
        # print("Message name: %s. Data: %s" % (msg_name, data))
        
    def lineReceived(self, data):
        if not data.startswith("%%"):
            print("Unknown message. Passing it")
        if data[2] == ">":
            self.process_request(data[3:])
        else:
            self.process_response(data[3:])
        
    # def dataReceived(self, data):
    #    print data
        
        
class ExtModuleFactory(ClientFactory):
    def startedConnecting(self, connector):
        print("Connection started")
        
    def buildProtocol(self, addr):
        print("Connected") 
        return ExtModuleProtocol()

    def clientConnectionLost(self, connector, reason):
        print("Lost connection. Reason: ", reason)
        time.sleep(2)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("Connection failed. Reason: ", reason)
        time.sleep(2)
        connector.connect()


def main():
    reactor.connectTCP(YATE_HOST, YATE_PORT, ExtModuleFactory())
    reactor.run()

if __name__ == '__main__':
    main()
