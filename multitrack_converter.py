"""
Script para convertir archivos MIDI monofónicos a versiones polifónicas
con diferentes instrumentos usando pretty_midi.
"""

import pretty_midi
import os

def convert_to_multitrack(input_midi_path, output_path, instrument_programs=[0, 24, 40]):
    """
    Convierte un archivo MIDI monofónico a una versión con múltiples instrumentos.
    
    Args:
        input_midi_path (str): Ruta al archivo MIDI de entrada
        output_path (str): Ruta donde guardar el archivo MIDI resultante
        instrument_programs (list): Lista de números de programa MIDI para los instrumentos
                                  Números de programa MIDI comunes:
                                  Vientos:
                                  - 56: Trumpet
                                  - 57: Trombone
                                  - 58: Tuba
                                  - 59: Muted Trumpet
                                  Cuerdas:
                                  - 24: Acoustic Guitar (nylon)
                                  - 25: Acoustic Guitar (steel)
                                  - 26: Electric Guitar (jazz)
                                  - 27: Electric Guitar (clean)
    """
    # Cargar el archivo MIDI original
    midi_data = pretty_midi.PrettyMIDI(input_midi_path)
    
    # Crear nuevo archivo MIDI
    new_midi = pretty_midi.PrettyMIDI(resolution=midi_data.resolution, initial_tempo=midi_data.estimate_tempo())
    
    # Para cada instrumento, crear un nuevo instrumento y copiar las notas
    for i, program in enumerate(instrument_programs):
        # Crear nuevo instrumento
        instrument = pretty_midi.Instrument(program=program, name=f"Instrument_{i}")
        
        # Obtener todas las notas del archivo original
        for old_note in midi_data.instruments[0].notes:
            # Crear nueva nota con un offset de octava para cada instrumento
            new_note = pretty_midi.Note(
                velocity=old_note.velocity,
                pitch=old_note.pitch + (i * 12),  # Transponer una octava arriba para cada instrumento
                start=old_note.start,
                end=old_note.end
            )
            instrument.notes.append(new_note)
        
        # Agregar el instrumento al nuevo archivo MIDI
        new_midi.instruments.append(instrument)
    
    # Guardar el archivo MIDI resultante
    new_midi.write(output_path)

def main():
    # Crear directorio si no existe
    os.makedirs("audios_generated", exist_ok=True)
    
    # Archivo de entrada
    input_file = "audios_generated/gen_audio_1.mid"
    
    # Definir combinaciones de instrumentos de viento y cuerda
    instrument_combinations = [
        # Combinación 1: Trompeta, Guitarra Acústica (nylon), Trombón
        [56, 24, 57],
        # Combinación 2: Trompeta con sordina, Guitarra Eléctrica (jazz), Tuba
        [59, 26, 58],
        # Combinación 3: Trompeta, Guitarra Acústica (steel), Trompeta con sordina
        [56, 25, 59]
    ]
    
    # Generar versiones con diferentes combinaciones de instrumentos
    for i, instruments in enumerate(instrument_combinations, 1):
        output_file = f"audios_generated/gen_audio_1_brass_strings_{i}.mid"
        print(f"Generando combinación {i} con instrumentos {instruments}...")
        convert_to_multitrack(input_file, output_file, instruments)
        print(f"Archivo guardado como {output_file}")

if __name__ == "__main__":
    main() 