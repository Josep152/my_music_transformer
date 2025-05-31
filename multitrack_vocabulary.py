"""
Vocabulario extendido para soportar eventos MIDI multitrack basado en Oore et al., 2018
pero adaptado para manejar múltiples instrumentos y polifonía.
"""

"""MANIFEST CONSTANTS"""

# Constantes originales
note_on_events = 128
note_off_events = note_on_events
time_shift_events = 125
velocity_events = 32

# Nuevas constantes para instrumentos
max_instruments = 16  # Número máximo de canales MIDI
instrument_events = 128  # Número de programas MIDI estándar

# Constantes de tiempo
LTH = 1000  # max milliseconds
DIV = LTH // time_shift_events  # 1 time_shift = DIV milliseconds
BIN_STEP = 128 // velocity_events

# Crear vocabulario extendido
note_on_vocab = [f"note_on_{i}_{inst}" for inst in range(max_instruments) for i in range(note_on_events)]
note_off_vocab = [f"note_off_{i}_{inst}" for inst in range(max_instruments) for i in range(note_off_events)]
time_shift_vocab = [f"time_shift_{i}" for i in range(time_shift_events)]
velocity_vocab = [f"set_velocity_{i}" for i in range(velocity_events)]
instrument_vocab = [f"set_instrument_{i}" for i in range(instrument_events)]

# Vocabulario completo
vocab = ['<pad>'] + note_on_vocab + note_off_vocab + time_shift_vocab + velocity_vocab + instrument_vocab + ['<start>', '<end>']
vocab_size = len(vocab)

# Tokens especiales
pad_token = vocab.index("<pad>")
start_token = vocab.index("<start>")
end_token = vocab.index("<end>")

"""HELPER FUNCTIONS"""

def events_to_indices(event_list, _vocab=None):
    """Convierte lista de eventos a índices en el vocabulario"""
    if _vocab is None:
        _vocab = vocab
    return [_vocab.index(event) for event in event_list]

def indices_to_events(index_list, _vocab=None):
    """Convierte lista de índices a eventos en el vocabulario"""
    if _vocab is None:
        _vocab = vocab
    return [_vocab[idx] for idx in index_list]

def velocity_to_bin(velocity, step=BIN_STEP):
    """Convierte velocidad MIDI (0-127) a un bin reducido"""
    if 128 % step != 0:
        raise ValueError("128 must be divisible by bins")
    if not (0 <= velocity <= 127):
        raise ValueError(f"velocity must be between 0 and 127, not {velocity}")
    return velocity // step

def bin_to_velocity(_bin, step=BIN_STEP):
    """Convierte bin de velocidad a velocidad MIDI (0-127)"""
    if not (0 <= _bin * step <= 127):
        raise ValueError(f"bin * step must be between 0 and 127 to be a midi velocity, not {_bin * step}")
    return int(_bin * step)

def time_to_events(delta_time, event_list=None, index_list=None, _vocab=None):
    """Traduce tiempo delta acumulado entre eventos MIDI al vocabulario"""
    if _vocab is None:
        _vocab = vocab
    time = time_cutter(delta_time)
    base_idx = len(note_on_vocab) + len(note_off_vocab)
    for i in time:
        idx = base_idx + i
        if event_list is not None:
            event_list.append(_vocab[idx])
        if index_list is not None:
            index_list.append(idx)

def time_cutter(time, lth=LTH, div=DIV):
    """
    Corta el tiempo en segmentos según el vocabulario definido
    """
    if lth % div != 0:
        raise ValueError("lth must be divisible by div")

    time_shifts = []
    for i in range(time // lth):
        time_shifts.append(round_(lth / div))
    leftover_time_shift = round_((time % lth) / div)
    if leftover_time_shift > 0:
        time_shifts.append(leftover_time_shift)
    return time_shifts

def round_(a):
    """Función de redondeo personalizada"""
    b = a // 1
    decimal_digits = a % 1
    adder = 1 if decimal_digits >= 0.5 else 0
    return int(b + adder)

def get_note_event_indices(note, instrument, is_on=True):
    """
    Obtiene los índices para eventos de nota considerando el instrumento
    
    Args:
        note (int): número de nota MIDI (0-127)
        instrument (int): número de instrumento (0-15)
        is_on (bool): True para note_on, False para note_off
    
    Returns:
        int: índice en el vocabulario
    """
    if not (0 <= note <= 127):
        raise ValueError(f"note must be between 0 and 127, not {note}")
    if not (0 <= instrument < max_instruments):
        raise ValueError(f"instrument must be between 0 and {max_instruments-1}, not {instrument}")
    
    base = 1  # Skip pad token
    if not is_on:
        base += len(note_on_vocab)
    
    return base + (instrument * note_on_events) + note 