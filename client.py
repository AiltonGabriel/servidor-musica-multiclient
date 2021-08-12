# AUDIOclient3.py
# coding: utf-8

# Para instalar o pyaudio:
# conda install pyaudio

import socket
import pyaudio
import pickle

serverName = '127.0.0.1'
serverPort = 12000
musicListServerPort = 13000

def get_music_list():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((serverName, musicListServerPort))
    music_list = pickle.loads(client_socket.recv(4096))
    music_list.append({'title': 'Sair'})
    return music_list


def main():

    while(True):
        music_list = get_music_list()

        for i, musica in enumerate(music_list):
            print("{} - {}".format(i + 1, musica['title']))

        indice_musica = int(input("Digite o código da música escolhida: ")) - 1

        if(indice_musica >= 0 and indice_musica < len(music_list)):
            if(indice_musica != len(music_list) - 1):

                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((serverName, serverPort))

                musica = music_list[indice_musica]
                data_string = pickle.dumps(musica)
                client_socket.send(data_string)

                p = pyaudio.PyAudio()

                FORMAT = 8
                CHANNELS = 2
                RATE = 44100
                CHUNK = 1024 * 4

                stream = p.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                output=True,
                                frames_per_buffer=CHUNK)

                while True:
                    content = client_socket.recv(CHUNK)
                    if content:
                        stream.write(content) 
                    else:
                        break
                    
                print("Audio executado")

                stream.close()
                p.terminate()
            else:
                break
        else:
            print("Código Inválido!")
            break

        client_socket.close() 

if __name__ == '__main__':
	main()