import random
import string
from django.apps import apps

def generate_unique_code(lenght:int = 6) -> str:
    """Generates a random string that pretends to be the
    unique in terms of room.models.Rooms.code

    Args:
        lenght (int, optional): Length of the code. Defaults to 6.

    Returns:
        str: The generated code
    """
    Rooms = apps.get_model('room','Rooms')
    PaidUsers = apps.get_model('user', 'PaidUsers')
    Commerces = apps.get_model('user', 'Commerces')
    while True:
        code = ''.join(
            random.choices(string.ascii_uppercase, k=lenght),
        )
        lenght += 1
        anonymous = Rooms.objects.filter(code = code).exists()
        paid_users = PaidUsers.objects.filter(exclusive_code = code).exists()
        commerce = Commerces.objects.filter(exclusive_code = code).exists() 
        if not anonymous or paid_users or commerce:
            break
        
    return code
