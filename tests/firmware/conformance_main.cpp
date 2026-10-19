// Conformance replay: runs recorded Python StationCore traces through the C++
// port and compares step counts exactly and emitted messages field by field.
//
//   conformance_main <trace.json | trace_dir> ...
//
// Exit status 0 only if every event of every trace matches. The core itself is
// allocation-free; this harness (test code) uses the standard library freely.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "station_core.h"

namespace {

using roomcleaner::winch::OutMsg;
using roomcleaner::winch::StationCore;

// ------------------------------------------------------- test-side JSON DOM
struct Node {
  enum T { Null, Bool, Int, Flt, Str, Obj, Arr } t = Null;
  bool b = false;
  long long i = 0;
  double d = 0;
  std::string s;
  std::vector<std::pair<std::string, Node>> obj;
  std::vector<Node> arr;
  const Node* get(const std::string& k) const {
    for (const auto& kv : obj)
      if (kv.first == k) return &kv.second;
    return nullptr;
  }
};

struct Parser {
  const std::string& s;
  size_t p = 0;
  bool bad = false;
  explicit Parser(const std::string& str) : s(str) {}
  void ws() { while (p < s.size() && (s[p] == ' ' || s[p] == '\n' || s[p] == '\r' || s[p] == '\t')) ++p; }
  bool lit(const char* l) {
    size_t n = std::char_traits<char>::length(l);
    if (s.compare(p, n, l) == 0) { p += n; return true; }
    return false;
  }
  std::string str() {
    std::string out;
    ++p;  // opening quote
    while (p < s.size() && s[p] != '"') {
      char c = s[p++];
      if (c != '\\') { out += c; continue; }
      char x = s[p++];
      switch (x) {
        case 'n': out += '\n'; break;
        case 't': out += '\t'; break;
        case 'r': out += '\r'; break;
        case 'b': out += '\b'; break;
        case 'f': out += '\f'; break;
        case 'u': {
          int cp = std::stoi(s.substr(p, 4), nullptr, 16);
          p += 4;
          out += static_cast<char>(cp);   // traces are ASCII-only
          break;
        }
        default: out += x;
      }
    }
    ++p;
    return out;
  }
  Node value() {
    ws();
    Node n;
    if (p >= s.size()) { bad = true; return n; }
    char c = s[p];
    if (c == '{') {
      n.t = Node::Obj;
      ++p; ws();
      if (s[p] == '}') { ++p; return n; }
      while (true) {
        ws();
        std::string k = str();
        ws();
        if (s[p] != ':') { bad = true; return n; }
        ++p;
        n.obj.emplace_back(k, value());
        ws();
        if (s[p] == ',') { ++p; continue; }
        if (s[p] == '}') { ++p; break; }
        bad = true; return n;
      }
    } else if (c == '[') {
      n.t = Node::Arr;
      ++p; ws();
      if (s[p] == ']') { ++p; return n; }
      while (true) {
        n.arr.push_back(value());
        ws();
        if (s[p] == ',') { ++p; continue; }
        if (s[p] == ']') { ++p; break; }
        bad = true; return n;
      }
    } else if (c == '"') {
      n.t = Node::Str;
      n.s = str();
    } else if (lit("true")) { n.t = Node::Bool; n.b = true; }
    else if (lit("false")) { n.t = Node::Bool; n.b = false; }
    else if (lit("null")) { n.t = Node::Null; }
    else {
      size_t q = p;
      bool flt = false;
      while (q < s.size() && (std::isdigit(static_cast<unsigned char>(s[q])) || s[q] == '-' || s[q] == '+' ||
                              s[q] == '.' || s[q] == 'e' || s[q] == 'E')) {
        if (s[q] == '.' || s[q] == 'e' || s[q] == 'E') flt = true;
        ++q;
      }
      if (q == p) { bad = true; return n; }
      std::string tok = s.substr(p, q - p);
      p = q;
      if (flt) { n.t = Node::Flt; n.d = std::strtod(tok.c_str(), nullptr); }
      else { n.t = Node::Int; n.i = std::strtoll(tok.c_str(), nullptr, 10); }
    }
    return n;
  }
};

bool parse(const std::string& text, Node& out) {
  Parser ps(text);
  out = ps.value();
  ps.ws();
  return !ps.bad && ps.p == text.size();
}

// ------------------------------------------------------------- comparison
std::string describe(const Node& n) {
  switch (n.t) {
    case Node::Null: return "null";
    case Node::Bool: return n.b ? "true" : "false";
    case Node::Int: return std::to_string(n.i) + " (int)";
    case Node::Flt: { char b[48]; std::snprintf(b, sizeof b, "%.17g (float)", n.d); return b; }
    case Node::Str: return "\"" + n.s + "\"";
    case Node::Obj: return "{...}";
    case Node::Arr: return "[...]";
  }
  return "?";
}

// Returns an empty string when equal, otherwise a mismatch description.
std::string compareNode(const Node& exp, const Node& act, const std::string& path) {
  if (exp.t != act.t)
    return path + ": expected " + describe(exp) + ", got " + describe(act);
  switch (exp.t) {
    case Node::Null: return "";
    case Node::Bool: return exp.b == act.b ? "" : path + ": expected " + describe(exp) + ", got " + describe(act);
    case Node::Int: return exp.i == act.i ? "" : path + ": expected " + describe(exp) + ", got " + describe(act);
    case Node::Str: return exp.s == act.s ? "" : path + ": expected " + describe(exp) + ", got " + describe(act);
    case Node::Flt: {
      const double tol = 1e-6 * std::max(std::fabs(exp.d), std::fabs(act.d)) + 1e-12;
      return std::fabs(exp.d - act.d) <= tol ? "" : path + ": expected " + describe(exp) + ", got " + describe(act);
    }
    case Node::Obj: {
      for (const auto& kv : exp.obj) {
        const Node* a = act.get(kv.first);
        if (!a) return path + "." + kv.first + ": missing in C++ output";
        std::string r = compareNode(kv.second, *a, path + "." + kv.first);
        if (!r.empty()) return r;
      }
      for (const auto& kv : act.obj)
        if (!exp.get(kv.first)) return path + "." + kv.first + ": unexpected extra field in C++ output";
      return "";
    }
    case Node::Arr: return "arrays not used";
  }
  return "";
}

struct Stats {
  long events = 0, updates = 0, handles = 0, messages = 0, steps_nonzero = 0, dropped_datagrams = 0;
};

// Drains the core's outbox and compares with the expected "out" array (may be null).
std::string compareOut(StationCore& core, const Node* expOut) {
  std::vector<OutMsg> got;
  OutMsg m;
  while (core.drain(m)) got.push_back(m);
  const size_t nexp = expOut ? expOut->arr.size() : 0;
  if (got.size() != nexp) {
    std::string r = "message count: expected " + std::to_string(nexp) + ", got " + std::to_string(got.size());
    for (const auto& g : got) r += "\n      C++ emitted: " + std::string(g.data, g.len);
    return r;
  }
  for (size_t k = 0; k < nexp; ++k) {
    const Node& e = expOut->arr[k];
    const OutMsg& g = got[k];
    if (g.len > roomcleaner::winch::json::kMaxDatagram) return "datagram exceeds MAX_DATAGRAM";
    if (g.len != std::char_traits<char>::length(g.data)) return "datagram length/NUL mismatch";
    const std::string dest = e.get("d")->s;
    if ((dest == "*") != g.broadcast) return "msg[" + std::to_string(k) + "]: destination mismatch (expected " + dest + ")";
    Node act;
    if (!parse(std::string(g.data, g.len), act)) return "msg[" + std::to_string(k) + "]: C++ output is not valid JSON: " + std::string(g.data, g.len);
    std::string r = compareNode(*e.get("m"), act, "msg[" + std::to_string(k) + "]");
    if (!r.empty()) return r + "\n      C++ emitted: " + std::string(g.data, g.len);
  }
  return "";
}

bool replay(const std::string& file, Stats& st) {
  std::ifstream in(file, std::ios::binary);
  if (!in) { std::fprintf(stderr, "cannot open %s\n", file.c_str()); return false; }
  std::stringstream ss;
  ss << in.rdbuf();
  Node tr;
  if (!parse(ss.str(), tr)) { std::fprintf(stderr, "%s: trace is not valid JSON\n", file.c_str()); return false; }
  const std::string name = tr.get("name")->s;
  StationCore core(static_cast<uint32_t>(tr.get("boot")->i), tr.get("period_us")->i);
  std::string r = compareOut(core, tr.get("init_out"));
  if (!r.empty()) { std::printf("FAIL %s init: %s\n", name.c_str(), r.c_str()); return false; }
  const Node& events = *tr.get("events");
  for (size_t idx = 0; idx < events.arr.size(); ++idx) {
    const Node& ev = events.arr[idx];
    const std::string op = ev.get("op")->s;
    const long long now = ev.get("now")->i;
    ++st.events;
    if (op == "h") {
      ++st.handles;
      const std::string& raw = ev.get("raw")->s;
      const bool acc = core.handleDatagram(raw.data(), raw.size(), now, ev.get("host")->b);
      if (acc != ev.get("acc")->b) {
        std::printf("FAIL %s event %zu (t=%lld) handle: datagram accepted=%d, expected %d\n      raw: %s\n", name.c_str(),
                    idx, now, acc, ev.get("acc")->b, raw.c_str());
        return false;
      }
      if (!acc) ++st.dropped_datagrams;
    } else {
      ++st.updates;
      const Node* encn = ev.get("enc");
      const bool present = encn->t != Node::Null;
      const int steps = core.update(now, present ? encn->i : 0, ev.get("ev")->b, ev.get("sw")->b, present);
      if (steps != ev.get("steps")->i) {
        std::printf("FAIL %s event %zu (t=%lld) update: steps expected %lld, got %d\n", name.c_str(), idx, now,
                    ev.get("steps")->i, steps);
        return false;
      }
      if (steps) ++st.steps_nonzero;
    }
    const Node* eo = ev.get("out");
    if (eo) st.messages += static_cast<long>(eo->arr.size());
    r = compareOut(core, eo);
    if (!r.empty()) {
      std::printf("FAIL %s event %zu (t=%lld, op=%s): %s\n", name.c_str(), idx, now, op.c_str(), r.c_str());
      return false;
    }
  }
  if (core.droppedMessages() != 0) {
    std::printf("FAIL %s: outbox dropped %u messages\n", name.c_str(), core.droppedMessages());
    return false;
  }
  std::printf("ok   %-26s %6zu events\n", name.c_str(), events.arr.size());
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  std::vector<std::string> files;
  for (int a = 1; a < argc; ++a) {
    std::filesystem::path p(argv[a]);
    if (std::filesystem::is_directory(p)) {
      for (const auto& e : std::filesystem::directory_iterator(p))
        if (e.path().extension() == ".json") files.push_back(e.path().string());
    } else {
      files.push_back(p.string());
    }
  }
  std::sort(files.begin(), files.end());
  if (files.empty()) { std::fprintf(stderr, "usage: %s <trace.json|dir> ...\n", argv[0]); return 2; }
  Stats st;
  int failed = 0;
  for (const auto& f : files)
    if (!replay(f, st)) ++failed;
  std::printf("%d trace(s), %d failed; %ld events (%ld updates, %ld datagrams, %ld dropped), %ld messages compared, "
              "%ld non-zero step outputs\n",
              static_cast<int>(files.size()), failed, st.events, st.updates, st.handles, st.dropped_datagrams,
              st.messages, st.steps_nonzero);
  return failed ? 1 : 0;
}
