"""Forward Alertmanager notifications to Discord as color-coded embeds."""

import json
import logging
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def send_discord_notification(alert):
    """Send one Discord embed per alert with a distinct status color."""
    status = alert.get("status", "unknown").lower()
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    name = labels.get("alertname", "Unknown Alert")

    embed = {
        "title": f"{status.upper()} — {name}",
        "description": annotations.get("summary", name),
        "color": 0xE74C3C if status == "firing" else 0x2ECC71,
        "timestamp": alert.get("endsAt" if status == "resolved" else "startsAt"),
        "footer": {"text": "SAIL Monitoring"},
    }

    request = urllib.request.Request(
        DISCORD_WEBHOOK,
        data=json.dumps({"embeds": [embed]}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SAIL-Alertmanager/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10):
        logger.info("Sent %s notification for %s", status, name)


class AlertHandler(BaseHTTPRequestHandler):
    """Receive Alertmanager webhook notifications."""

    def do_POST(self):
        """Forward each alert to Discord individually."""
        if self.path != "/alerts":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))

            for alert in payload.get("alerts", []):
                send_discord_notification(alert)

        except (ValueError, TypeError) as error:
            logger.warning("Invalid alert payload: %s", error)
            self.send_error(400)
            return

        except (urllib.error.URLError, TimeoutError) as error:
            logger.error("Discord delivery failed: %s", error)
            self.send_error(502)
            return

        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), AlertHandler).serve_forever()