#pragma once
// Records handlers; the test harness invokes them with chosen query arguments and reads the reply.
#include <functional>
#include <map>
#include <string>
#include "Arduino.h"
enum HTTPMethod { HTTP_GET, HTTP_POST };
struct ClientStub { void write(const uint8_t*, size_t) {} };
class WebServer {
 public:
  explicit WebServer(int) {}
  typedef void (*Handler)();
  void on(const char* path, HTTPMethod, Handler h) { handlers[path] = h; }
  void begin() {}
  void handleClient() {}
  bool hasArg(const char* k) const { return args.count(k) > 0; }
  String arg(const char* k) const { auto it = args.find(k); return it == args.end() ? String("") : String(it->second); }
  void sendHeader(const char*, const String&) {}
  void setContentLength(size_t) {}
  void send(int code, const char* /*type*/, const String& body) { last_code = code; last_body = body.c_str(); }
  ClientStub& client() { return c; }
  // test side
  std::map<std::string, Handler> handlers;
  std::map<std::string, std::string> args;
  int last_code = 0;
  std::string last_body;
 private:
  ClientStub c;
};
