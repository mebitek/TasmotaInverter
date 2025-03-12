import struct

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
