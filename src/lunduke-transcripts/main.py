"""
Main entry point for lunduke-transcripts.

Created on 2026-03-06 by Anonymous.
"""

import argparse


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="lunduke-transcripts",
        description="lunduke-transcripts - AI-agent project",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    parser.add_argument(
        "name",
        nargs="?",
        default="World",
        help="Name to greet (default: World)",
    )

    args = parser.parse_args()
    print(f"Hello from lunduke-transcripts, {args.name}!")


if __name__ == "__main__":
    main()
