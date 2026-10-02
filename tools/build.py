#!/usr/bin/env python3
"""Build the academic website, then its approved photography gallery."""
from __future__ import annotations
import json
import sys
import _profile_builder as profile
import publish_gallery


def main() -> None:
    profile.main()
    publish_gallery.main()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
