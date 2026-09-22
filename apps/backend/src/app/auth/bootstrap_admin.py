import argparse
import asyncio
import sys
from getpass import getpass

from pydantic import ValidationError

from app.auth.errors import AuthenticationError
from app.auth.repository import AuthRepository
from app.auth.service import AuthService
from app.db.session import async_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the first CyVerse administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--team")
    return parser


async def create_admin(
    *, username: str, display_name: str, team: str | None, password: str
) -> None:
    async with async_session_factory() as session:
        service = AuthService(AuthRepository(session))
        user = await service.bootstrap_admin(
            username=username,
            password=password,
            display_name=display_name,
            team=team,
        )
    print(f"Created administrator '{user.username}'.")


def main() -> None:
    args = build_parser().parse_args()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
        asyncio.run(
            create_admin(
                username=args.username,
                display_name=args.display_name,
                team=args.team,
                password=password,
            ),
            loop_factory=loop_factory,
        )
    except ValidationError as error:
        raise SystemExit(
            "Invalid account details. Check the username format and password length."
        ) from error
    except AuthenticationError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
