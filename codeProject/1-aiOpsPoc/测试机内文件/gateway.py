import cherrypy
import requests

FLASK_BASE = "http://127.0.0.1:5000"

class gateway(object):
    exposed = True

    def GET(self, *args, **kwargs):
        return self._proxy(*args, **kwargs)

    def POST(self, *args, **kwargs):
        return self._proxy(*args, **kwargs)

    def _proxy(self, *args, **kwargs):
        path = "/" + "/".join(args) if args else "/"
        target = FLASK_BASE + path
        qs = cherrypy.request.query_string
        if qs:
            target += "?" + qs

        method = cherrypy.request.method
        headers = {
            k: v for k, v in cherrypy.request.headers.items()
            if k.lower() not in ("host", "connection", "content-length")
        }
        body = cherrypy.request.body.read() if method in ("POST", "PUT", "PATCH") else None

        try:
            resp = requests.request(
                method=method, url=target, headers=headers,
                data=body, timeout=30,
            )
        except requests.RequestException as e:
            cherrypy.response.status = 502
            return "Gateway error: %s" % str(e)

        cherrypy.response.status = resp.status_code
        for k, v in resp.headers.items():
            if k.lower() not in ("connection", "transfer-encoding", "content-encoding"):
                cherrypy.response.headers[k] = v
        return resp.content