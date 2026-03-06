"""Entry point for running djinsight MCP server: python -m djinsight.mcp"""

import os
import sys


def main():
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not settings_module:
        print(
            "Error: DJANGO_SETTINGS_MODULE environment variable is required.\n"
            "Example: DJANGO_SETTINGS_MODULE=myproject.settings python -m djinsight.mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    import django

    django.setup()

    from djinsight.mcp.server import mcp

    mcp.run()


if __name__ == "__main__":
    main()
