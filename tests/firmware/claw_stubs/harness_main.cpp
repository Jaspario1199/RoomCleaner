// Host harness for firmware/claw_s3: runs setup(), then each argv entry "PATH?k=v&k=v" through the registered
// handler and prints one JSON line {"code":..,"body":..,"servo_us":..}. Test code only.
#include "claw_s3.ino"
#include <sstream>
int main(int argc, char** argv) {
  setup();
  loop();
  std::printf("{\"boot_servo_us\":%d}\n", g_servo_us);
  for (int i = 1; i < argc; i++) {
    std::string q = argv[i], path = q, rest;
    size_t k = q.find('?');
    if (k != std::string::npos) { path = q.substr(0, k); rest = q.substr(k + 1); }
    server.args.clear();
    std::stringstream ss(rest);
    std::string kv;
    while (std::getline(ss, kv, '&')) {
      size_t e = kv.find('=');
      if (e != std::string::npos) server.args[kv.substr(0, e)] = kv.substr(e + 1);
    }
    auto it = server.handlers.find(path);
    if (it == server.handlers.end()) { std::printf("{\"code\":404}\n"); continue; }
    server.last_code = 0;
    it->second();
    std::printf("{\"code\":%d,\"body\":%s,\"servo_us\":%d}\n", server.last_code,
                server.last_body.empty() ? "null" : server.last_body.c_str(), g_servo_us);
  }
  return 0;
}
