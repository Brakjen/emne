"""Generate a bcrypt hash for the admin password.

Usage: python -m scripts.hash_password <password>
"""
import sys
import bcrypt


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.hash_password <password>")
        sys.exit(1)
    password = sys.argv[1]
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    print(f"\nHash: {hashed}")
    print(f"\nSet this as EMNE_AUTH_PASSWORD_HASH in your environment.")


if __name__ == "__main__":
    main()
