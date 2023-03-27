import network
import socket
import time
import re
import config
import uos
import uasyncio as asyncio
import _thread
import ujson as json
from response import Response
from request import Request

class GurgleAppsWebserver:

    def __init__(self, wifi_ssid, wifi_password, port=80, timeout=20, doc_root="/www"):
        print("GurgleApps.com Webserver")
        self.port = port
        self.timeout = timeout
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.doc_root = doc_root
        self.function_routes=[]
        # wifi client in station mode so we can connect to an access point
        self.wlan = network.WLAN(network.STA_IF)
        # activate the interface
        self.wlan.active(True)
        # connect to the access point with the ssid and password
        self.wlan.connect(self.wifi_ssid, self.wifi_password)

        self.html = """<!DOCTYPE html>
        <html>
            <head> <title>GurgleApps.com Webserver</title> </head>
            <body> <h1>Pico W</h1>
                <p>%s</p>
            </body>
        </html>
        """
        counter = self.timeout
        while counter > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            counter -= 1
            print('waiting for connection...')
            time.sleep(1)

        if self.wlan.status() != 3:
            raise RuntimeError('network connection failed')
        else:
            print('connected')
            status = self.wlan.ifconfig()
            print('ip = ' + status[0])
        self.serving = True
        print('point your browser to http://', status[0])
        try:
            pass
            #asyncio.run(self.start_server())
        except OSError as e:
            print(e)
        finally:
            asyncio.new_event_loop()
        print("exit constructor")

    async def start_server(self):
            asyncio.create_task(asyncio.start_server(self.serve_request, "0.0.0.0", 80))
            while self.serving:
                await asyncio.sleep(1)
                
    def add_function_route(self, route, function):
       self.function_routes.append({"route":route, "function":function})
            

    async def serve_request(self, reader, writer):
        try:
            url = ""
            method = ""
            content_length = 0
            # Read the request line by line because we want the post data potentially
            headers = []
            post_data = None
            while True:
                line = await reader.readline()
                line = line.decode('utf-8').strip()
                if line == "":
                    break
                headers.append(line)
            request_raw = str("\r".join(headers))
            print(request_raw)
            request_pattern = re.compile(r"(GET|POST)\s+([^\s]+)\s+HTTP")
            match = request_pattern.search(request_raw)
            if match:
                method = match.group(1)
                url = match.group(2)
                print(method, url)
            # extract content length for POST requests
            if method == "POST":
                content_length_pattern = re.compile(r"Content-Length:\s+(\d+)")
                match = content_length_pattern.search(request_raw)
                if match:
                    content_length = int(match.group(1))
                    print("content_length: "+str(content_length))
            # Read the POST data if there's any
            if content_length > 0:
                post_data_raw = await reader.readexactly(content_length)
                print("POST data:", post_data_raw)
                post_data = json.loads(post_data_raw)
            request = Request(post_data)
            response = Response(writer)
            # check if the url is a function route and if so run the function
            path_components = self.get_path_components(url)
            print("path_components: "+str(path_components))
            route_function, params = self.match_route(path_components)
            if route_function:
                print("calling function: "+str(route_function)+" with params: "+str(params))
                await route_function(request, response, *params)
                return
            # perhaps it is a file
            file = self.get_file(self.doc_root + url)
            print("file: "+str(file))
            if file:
                print("file found so serving it")
                print(file)
                writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                writer.write(file)
                await writer.drain()
                await writer.wait_closed()
                return
            print("file not found")
            response = self.html % "page not found "+url
            writer.write('HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n')
            writer.write(response)
            await writer.drain()
            await writer.wait_closed()
            if (url == "/shutdown"):
                self.serving = False
        except OSError as e:
            print(e)

    def get_file(self, filename):
        print("getFile: "+filename)
        try :
            # Check if the file exists
            if uos.stat(filename)[6] > 0:
                # Open the file in read mode
                with open(filename, "r") as f:
                    # Read the contents of the file into a string
                    return f.read()
            else:
                # The file doesn't exist
                return False
        except OSError as e:
            # print the error
            print(e)
            return False
        
    def get_path_components(self, path):
        return tuple(filter(None, path.split('/')))
    
    def match_route(self, path_components):
        for route in self.function_routes:
            route_pattern = list(filter(None, route["route"].split("/")))
            print("route_pattern: "+str(route_pattern))
            if len(route_pattern) != len(path_components):
                continue
            match = True
            params = []
            for idx, pattern_component in enumerate(route_pattern):
                print("pattern_component: "+pattern_component+" path_component: "+path_components[idx])
                if pattern_component.startswith('<') and pattern_component.endswith('>'):
                    param_value = path_components[idx]
                    params.append(param_value)
                else:
                    if pattern_component != path_components[idx]:
                        match = False
                        break
            if match:
                return route["function"], params
        return None, []



