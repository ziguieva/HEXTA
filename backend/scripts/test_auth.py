from getpass import getpass

from app.services.auth_service import authenticate_user


def main():
    print("=== BANKKEY HSM | AUTHENTICATION TEST ===")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    user = authenticate_user(username, password)

    if user is None:
        print("[DENIED] Authentication failed")
        return

    print("[OK] Authentication successful")
    print("Username:", user["username"])
    print("Role:", user["role"])

    wrong_password = password + "-INVALID"

    rejected = authenticate_user(username, wrong_password)

    if rejected is None:
        print("[OK] Incorrect password rejected")
    else:
        raise AssertionError(
            "SECURITY FAILURE: incorrect password accepted"
        )

    print("=== AUTHENTICATION TEST PASSED ===")


if __name__ == "__main__":
    main()
