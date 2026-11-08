import json
import logging
import traceback
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlsplit, unquote



from slai.db import init_db
from slai.api.routes import (
    run_audit_from_payload,
    save_document,
    get_deal_documents,
    get_audit_history,
)
from slai.api.auth_routes import login_user, register_user
from slai.auth import decode_access_token, has_permission
from slai.skills import list_skills, run_skill
from slai.storage import (
    load_deals,
    add_deal,
    update_deal,
    delete_deal,
    get_deal,
)



MAX_BODY_SIZE = 2 * 1024 * 1024



PUBLIC_SKILLS = {
    "documents_ai",
    "audit",
}



AUTH_ROUTES = {
    ("api", "auth", "register"),
    ("api", "auth", "login"),
}



class APIError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code



class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True



def json_default(value):
    if is_dataclass(value):
        return asdict(value)


    if isinstance(value, Enum):
        return value.value


    if isinstance(value, (datetime, date)):
        return value.isoformat()


    if isinstance(value, Decimal):
        return str(value)


    raise TypeError(
        f"Object of type {type(value).__name__} "
        "is not JSON serializable"
    )



class SLAIHandler(SimpleHTTPRequestHandler):
    def get_request_path(self):
        return urlsplit(self.path).path


    def get_path_parts(self):
        path = self.get_request_path().strip("/")


        return [
            unquote(part)
            for part in path.split("/")
            if part
        ]


    def read_json_body(self):
        content_type = (
            self.headers.get("Content-Type", "")
            .split(";")[0]
            .strip()
            .lower()
        )


        if content_type != "application/json":
            raise APIError(
                "Content-Type must be application/json",
                415,
            )


        content_length_header = self.headers.get("Content-Length")


        if not content_length_header:
            raise APIError(
                "Content-Length is required",
                411,
            )


        try:
            content_length = int(content_length_header)
        except ValueError:
            raise APIError(
                "invalid Content-Length",
                400,
            )


        if content_length < 0:
            raise APIError(
                "invalid Content-Length",
                400,
            )


        if content_length > MAX_BODY_SIZE:
            raise APIError(
                "request body is too large",
                413,
            )


        raw_body = self.rfile.read(content_length)


        try:
            return json.loads(raw_body.decode("utf-8"))
        except UnicodeDecodeError:
            raise APIError(
                "request must be UTF-8",
                400,
            )
        except json.JSONDecodeError:
            raise APIError(
                "invalid JSON",
                400,
            )


    def parse_deal_id(self, parts):
        if len(parts) < 3:
            raise APIError("deal id is required", 400)


        try:
            return int(parts[2])
        except ValueError:
            raise APIError(
                "deal id must be an integer",
                400,
            )


    def get_current_user(self):
        header = self.headers.get("Authorization", "")


        if not header.startswith("Bearer "):
            raise APIError("authorization required", 401)


        token = header.removeprefix("Bearer ").strip()


        try:
            return decode_access_token(token)
        except Exception:
            raise APIError("invalid or expired token", 401)


    def require_permission(self, user, permission):
        if not has_permission(user, permission):
            raise APIError("forbidden", 403)


    def do_GET(self):
        try:
            parts = self.get_path_parts()
            path = self.get_request_path()


            if not path.startswith("/api/"):
                return super().do_GET()


            user = self.get_current_user()


            if parts == ["api", "deals"]:
                self.require_permission(user, "deal:read")
                return self.send_json(load_deals())


            if parts == ["api", "skills"]:
                self.require_permission(user, "deal:read")
                return self.send_json(
                    {
                        "skills": list_skills(),
                    }
                )


            if (
                len(parts) == 4
                and parts[0] == "api"
                and parts[1] == "deals"
                and parts[3] == "audits"
            ):
                self.require_permission(user, "deal:read")
                deal_id = self.parse_deal_id(parts)
                history = get_audit_history(deal_id)


                return self.send_json(history)


            if (
                len(parts) == 4
                and parts[0] == "api"
                and parts[1] == "deals"
                and parts[3] == "documents"
            ):
                self.require_permission(user, "deal:read")
                deal_id = self.parse_deal_id(parts)
                documents = get_deal_documents(deal_id)


                return self.send_json(documents)


            if (
                len(parts) == 3
                and parts[0] == "api"
                and parts[1] == "deals"
            ):
                self.require_permission(user, "deal:read")
                deal_id = self.parse_deal_id(parts)
                deal = get_deal(deal_id)


                if deal is None:
                    raise APIError(
                        "deal not found",
                        404,
                    )


                return self.send_json(deal)


            raise APIError("not found", 404)


        except APIError as error:
            return self.handle_api_error(error)
        except Exception:
            return self.handle_unexpected_error()


    def do_POST(self):
        try:
            parts = self.get_path_parts()
            body = self.read_json_body()


            if tuple(parts) in AUTH_ROUTES:
                if parts == ["api", "auth", "register"]:
                    result = register_user(body)
                    return self.send_json(result, status_code=201)


                if parts == ["api", "auth", "login"]:
                    result = login_user(body)
                    return self.send_json(result)


            user = self.get_current_user()


            if (
                len(parts) == 3
                and parts[0] == "api"
                and parts[1] == "skills"
            ):
                skill_name = parts[2]
                self.require_permission(user, "audit:run")


                if skill_name not in PUBLIC_SKILLS:
                    raise APIError(
                        "skill not found",
                        404,
                    )


                result = run_skill(skill_name, body)
                return self.send_json(result)


            if (
                len(parts) == 4
                and parts[0] == "api"
                and parts[1] == "deals"
                and parts[3] == "documents"
            ):
                self.require_permission(user, "document:write")
                deal_id = self.parse_deal_id(parts)
                result = save_document(deal_id, body)
                return self.send_json(
                    result,
                    status_code=201,
                )


            if parts == ["api", "audit"]:
                self.require_permission(user, "audit:run")
                result = run_audit_from_payload(body)
                return self.send_json(result)


            if parts == ["api", "deals"]:
                self.require_permission(user, "deal:write")
                deal_id = add_deal(body)
                deal = get_deal(deal_id)


                return self.send_json(
                    {
                        "status": "created",
                        "id": deal_id,
                        "deal": deal,
                    },
                    status_code=201,
                )


            raise APIError("not found", 404)


        except APIError as error:
            return self.handle_api_error(error)
        except ValueError as error:
            return self.handle_api_error(
                APIError(str(error), 422)
            )
        except Exception:
            return self.handle_unexpected_error()


    def do_PUT(self):
        try:
            parts = self.get_path_parts()


            user = self.get_current_user()
            self.require_permission(user, "deal:write")


            if (
                len(parts) != 3
                or parts[0] != "api"
                or parts[1] != "deals"
            ):
                raise APIError("not found", 404)


            deal_id = self.parse_deal_id(parts)
            body = self.read_json_body()


            updated = update_deal(deal_id, body)


            if not updated:
                raise APIError(
                    "deal not found",
                    404,
                )


            deal = get_deal(deal_id)


            return self.send_json(
                {
                    "status": "updated",
                    "id": deal_id,
                    "deal": deal,
                }
            )


        except APIError as error:
            return self.handle_api_error(error)
        except ValueError as error:
            return self.handle_api_error(
                APIError(str(error), 422)
            )
        except Exception:
            return self.handle_unexpected_error()


    def do_DELETE(self):
        try:
            parts = self.get_path_parts()


            user = self.get_current_user()
            self.require_permission(user, "deal:write")


            if (
                len(parts) != 3
                or parts[0] != "api"
                or parts[1] != "deals"
            ):
                raise APIError("not found", 404)


            deal_id = self.parse_deal_id(parts)
            deleted = delete_deal(deal_id)


            if not deleted:
                raise APIError(
                    "deal not found",
                    404,
                )


            return self.send_json(
                {
                    "status": "deleted",
                    "id": deal_id,
                }
            )


        except APIError as error:
            return self.handle_api_error(error)
        except ValueError as error:
            return self.handle_api_error(
                APIError(str(error), 422)
            )
        except Exception:
            return self.handle_unexpected_error()


    def send_json(self, data, status_code=200):
        payload = json.dumps(
            data,
            ensure_ascii=False,
            default=json_default,
        ).encode("utf-8")


        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(payload)),
        )
        self.end_headers()
        self.wfile.write(payload)


    def handle_api_error(self, error):
        return self.send_json(
            {
                "status": "error",
                "error": str(error),
            },
            status_code=error.status_code,
        )


    def handle_unexpected_error(self):
        traceback.print_exc()


        return self.send_json(
            {
                "status": "error",
                "error": "internal server error",
            },
            status_code=500,
        )



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )


    init_db()


    server = ThreadingHTTPServer(
        ("127.0.0.1", 8080),
        SLAIHandler,
    )


    print(
        "SLAI workflow server: http://127.0.0.1:8080"
    )


    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping SLAI server...")
    finally:
        server.server_close()