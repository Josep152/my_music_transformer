"""
Implementación del tokenizador para archivos MIDI multitrack, extendiendo el trabajo de Oore et al., 2018
para soportar múltiples instrumentos y polifonía.
"""

import mido
from multitrack_vocabulary import *
from dataclasses import dataclass
from typing import List, Dict, Optional
from torch import LongTensor

@dataclass
class MidiEvent:
    """Clase para representar un evento MIDI con toda la información necesaria"""
    type: str  # 'note_on', 'note_off', 'time_shift', 'set_velocity', 'set_instrument'
    note: Optional[int] = None
    velocity: Optional[int] = None
    instrument: Optional[int] = None
    time: Optional[int] = None
    program: Optional[int] = None

def midi_parser(fname=None, mid=None):
    """
    Traduce un archivo MIDI multitrack a la representación de vocabulario extendida.
    
    Args:
        fname (str): ruta al archivo MIDI a cargar O
        mid (mido.MidiFile): archivo MIDI ya cargado
        
    Returns:
        index_list (torch.Tensor): lista de índices en el vocabulario
        event_list (list): lista de eventos en el vocabulario
        tempo (int): tempo del archivo MIDI
    """
    if not ((fname is None) ^ (mid is None)):
        raise ValueError("Input one of fname or mid, not both or neither")

    if fname is not None:
        try:
            mid = mido.MidiFile(fname)
        except mido.midifiles.meta.KeySignatureError as e:
            raise ValueError(e)

    # Estructuras de datos para el procesamiento
    event_list = []
    index_list = []
    tempo = 0
    
    # Diccionario para mantener el estado de las notas activas por instrumento
    active_notes: Dict[int, Dict[int, int]] = {}  # instrument -> {note -> velocity}
    # Diccionario para mantener el programa (instrumento) asignado a cada canal
    channel_programs: Dict[int, int] = {}
    
    # Acumular todos los eventos con sus tiempos absolutos
    absolute_events: List[MidiEvent] = []
    current_time = 0
    
    # Primera pasada: recolectar todos los eventos con tiempos absolutos
    for track in mid.tracks:
        for msg in track:
            current_time += msg.time
            
            if msg.is_meta:
                if msg.type == "set_tempo" and tempo == 0:
                    tempo = msg.tempo
                continue
                
            if msg.type in ['note_on', 'note_off']:
                # Normalizar note_on con velocidad 0 a note_off
                if msg.type == 'note_on' and msg.velocity == 0:
                    msg_type = 'note_off'
                else:
                    msg_type = msg.type
                    
                # Obtener el programa/instrumento para este canal
                instrument = channel_programs.get(msg.channel, 0)
                
                absolute_events.append(MidiEvent(
                    type=msg_type,
                    note=msg.note,
                    velocity=msg.velocity,
                    instrument=instrument,
                    time=current_time
                ))
                
            elif msg.type == 'program_change':
                channel_programs[msg.channel] = msg.program
                absolute_events.append(MidiEvent(
                    type='set_instrument',
                    instrument=msg.channel,
                    program=msg.program,
                    time=current_time
                ))
    
    # Ordenar eventos por tiempo
    absolute_events.sort(key=lambda x: x.time)
    
    # Inicializar con token de inicio
    event_list.append('<start>')
    index_list.append(start_token)
    
    # Segunda pasada: convertir eventos a tokens
    last_time = 0
    for event in absolute_events:
        # Procesar tiempo delta
        if event.time > last_time:
            delta_time = event.time - last_time
            time_to_events(delta_time, event_list, index_list)
            last_time = event.time
            
        if event.type == 'set_instrument':
            # Agregar evento de cambio de instrumento
            event_str = f"set_instrument_{event.program}"
            event_list.append(event_str)
            index_list.append(vocab.index(event_str))
            
        elif event.type in ['note_on', 'note_off']:
            if event.type == 'note_on':
                # Agregar evento de velocidad si es note_on
                vel_bin = velocity_to_bin(event.velocity)
                vel_str = f"set_velocity_{vel_bin}"
                event_list.append(vel_str)
                index_list.append(vocab.index(vel_str))
                
            # Agregar evento de nota
            note_str = f"{event.type}_{event.note}_{event.instrument}"
            event_list.append(note_str)
            index_list.append(vocab.index(note_str))
    
    # Agregar token de fin
    event_list.append('<end>')
    index_list.append(end_token)
    
    return LongTensor(index_list), event_list, tempo

def list_parser(index_list=None, event_list=None, fname="output", tempo=512820):
    """
    Traduce una lista de eventos o índices del vocabulario extendido a un archivo MIDI multitrack.
    
    Args:
        index_list (list or torch.Tensor): lista de índices en el vocabulario O
        event_list (list): lista de eventos en el vocabulario
        fname (str, optional): nombre para el archivo MIDI generado
        tempo (int, optional): tempo del archivo MIDI en µs/beat
        
    Returns:
        mid (mido.MidiFile): archivo MIDI multitrack
    """
    if not ((index_list is None) ^ (event_list is None)):
        raise ValueError("Input one of index_list or event_list, not both or neither")

    if index_list is not None:
        try:
            if not all([isinstance(i.item(), int) for i in index_list]):
                raise ValueError("All indices in index_list must be int type")
        except AttributeError:
            if not all([isinstance(i, int) for i in index_list]):
                raise ValueError("All indices in index_list must be int type")
        event_list = indices_to_events(index_list)

    # Configurar archivo MIDI
    mid = mido.MidiFile()
    
    # Track de metadatos
    meta_track = mido.MidiTrack()
    meta_track.append(mido.MetaMessage("track_name", name=fname, time=0))
    meta_track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    mid.tracks.append(meta_track)
    
    # Diccionario para mantener tracks por instrumento
    instrument_tracks: Dict[int, mido.MidiTrack] = {}
    current_instrument = 0
    current_velocity = 64
    delta_time = 0
    
    # Procesar eventos
    for event in event_list:
        if event in ['<pad>', '<start>', '<end>']:
            continue
            
        if event.startswith('time_shift_'):
            # Acumular tiempo delta
            time_value = int(event.split('_')[-1])
            delta_time += time_value * DIV
            continue
            
        if event.startswith('set_velocity_'):
            # Actualizar velocidad actual
            vel_bin = int(event.split('_')[-1])
            current_velocity = bin_to_velocity(vel_bin)
            continue
            
        if event.startswith('set_instrument_'):
            # Cambiar instrumento actual
            program = int(event.split('_')[-1])
            current_instrument = program
            if current_instrument not in instrument_tracks:
                track = mido.MidiTrack()
                track.append(mido.Message('program_change', 
                                        program=program,
                                        channel=current_instrument % 16,
                                        time=0))
                instrument_tracks[current_instrument] = track
                mid.tracks.append(track)
            continue
            
        # Procesar eventos de nota
        if event.startswith(('note_on_', 'note_off_')):
            parts = event.split('_')
            note_type = parts[0] + '_' + parts[1]
            note = int(parts[2])
            instrument = int(parts[3])
            
            # Asegurarse de que existe el track para este instrumento
            if instrument not in instrument_tracks:
                track = mido.MidiTrack()
                track.append(mido.Message('program_change',
                                        program=0,  # default program
                                        channel=instrument % 16,
                                        time=0))
                instrument_tracks[instrument] = track
                mid.tracks.append(track)
            
            # Crear mensaje MIDI
            msg = mido.Message(
                'note_on' if note_type == 'note_on' else 'note_off',
                note=note,
                velocity=current_velocity if note_type == 'note_on' else 0,
                channel=instrument % 16,
                time=delta_time
            )
            
            # Agregar mensaje al track correspondiente
            instrument_tracks[instrument].append(msg)
            delta_time = 0  # Resetear delta time después de usar
    
    return mid 