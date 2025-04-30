import getpass
from plyer import notification


username = getpass.getuser()
notification.notify(
    title="Hello World",
    message=f"Hello {username}, welcome to the program!",
    timeout=10
)
