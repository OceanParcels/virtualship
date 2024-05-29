from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration
from virtual_ship.sailship import sailship

if __name__ == "__main__":
    config = VirtualShipConfiguration("student_input.json")
    sailship(config)
