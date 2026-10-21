// Test-only HTTP proxy in front of the API, so e2e tests can simulate an API outage and
// recovery without stopping real services. Forwards to TARGET; while "down" it refuses
// every request with a reset socket, like an unreachable server.
//   PORT    port to listen on (default 8099)
//   TARGET  API origin to forward to (default http://127.0.0.1:8012)
// Control: POST /__e2e/down and POST /__e2e/up (only these two paths are intercepted).
import http from "node:http";

const port = Number(process.env.PORT ?? 8099);
const target = new URL(process.env.TARGET ?? "http://127.0.0.1:8012");
let up = true;

http
  .createServer((request, response) => {
    if (request.method === "POST" && (request.url === "/__e2e/down" || request.url === "/__e2e/up")) {
      up = request.url.endsWith("/up");
      response.writeHead(204).end();
      return;
    }
    if (!up) {
      request.socket.destroy();
      return;
    }
    const upstream = http.request(
      { host: target.hostname, port: target.port, path: request.url, method: request.method, headers: request.headers },
      (reply) => {
        response.writeHead(reply.statusCode ?? 502, reply.headers);
        reply.pipe(response);
      },
    );
    upstream.on("error", () => response.writeHead(502).end());
    request.pipe(upstream);
  })
  .listen(port, "127.0.0.1", () => console.log(`toggle proxy on ${port} -> ${target.origin}`));
