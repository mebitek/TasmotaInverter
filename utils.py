import struct


def create_alarm_status(low_bat=False, high_bat=False, low_temp=False, high_temp=False, overload=False, poor_dc=False, low_ac=False, high_ac=False):
    status = 0

    status |= (1 if low_bat else 0) << 0     # Bit 0
    status |= (1 if high_bat else 0) << 1    # Bit 1
    status |= (1 if low_temp else 0) << 5    # Bit 5
    status |= (1 if high_temp else 0) << 6   # Bit 6
    status |= (1 if overload else 0) << 8    # Bit 8
    status |= (1 if poor_dc else 0) << 9      # Bit 9
    status |= (1 if low_ac else 0) << 10      # Bit 10
    status |= (1 if high_ac else 0) << 11     # Bit 11

    byte_array = [
        (status & 0xFF),
        (status >> 8) & 0xFF
    ]

    return byte_array

def create_capabilities_status(remote=False, relay=False, openpaygo=False, hibernation=False, load=False):
    status = 0

    status |= (1 if remote else 0) << 8    # Bit 8
    status |= (1 if relay else 0) << 17      # Bit 17
    status |= (1 if openpaygo else 0) << 27      # Bit 27
    status |= (1 if hibernation else 0) << 28     # Bit 28
    status |= (1 if load else 0) << 29     # Bit 29

    if 0 <= status <= 0xFFFFFFFF:
        byte_array = struct.pack('<I', status)  # '<I' per little-endian unsigned int

        return list(byte_array)

    return []

def convert_to_bytearray(value):
    byte_array = struct.pack('<I', value)
    return list(byte_array)

def convert_decimal(decimal_value):
    int_value = int(decimal_value * 100)  # 930
    if 0 <= int_value <= 65535:
        uint16_value = int_value
        byte_array = struct.pack('<H', uint16_value)  # '<H' per little-endian unsigned short
        return list(byte_array)
    return [0]

def convert_to_decimal(byte_array):
    if len(byte_array) != 2:
        return 0  # Ritorna 0 se l'array di byte non ha la lunghezza corretta

    # Usa struct per unpacking dei byte come unsigned short in formato little-endian
    uint16_value = struct.unpack('<H', bytes(byte_array))[0]  # 'H' per unsigned short
    decimal_value = uint16_value / 100.0  # Ritorna il valore decimale originale
    return decimal_value

def convert_negative(signed_value):
    if -32768 <= signed_value <= 32767:
        int16_value = signed_value
        byte_array = struct.pack('<h', int16_value)  # '<h' per little-endian signed short
        return list(byte_array)
    return []