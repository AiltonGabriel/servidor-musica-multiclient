# AUDIOclient3.py
# coding: utf-8

# Para instalar o pyaudio:
# conda install pyaudio

import socket
import pyaudio
import pickle
import struct

serverName = '127.0.0.1'
serverPort = 12000
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

data = clientSocket.recv(4096)
lista_musicas = pickle.loads(data)


while(True):
    
    for i, musica in enumerate(lista_musicas):
        print("{} - {}".format(i + 1, musica))

    indice_musica = int(input("Digite o código da música escolhida: ")) - 1

    clientSocket.send(struct.pack("L", indice_musica))

    if(indice_musica != len(lista_musicas) - 1):
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

        filesize = struct.unpack("L", clientSocket.recv(struct.calcsize("L")))[0]

        #print(filesize)

        current_size = 0

        while True:
            current_size += CHUNK
            if(current_size <= filesize):
                content = clientSocket.recv(CHUNK)
                stream.write(content)  # "Player" de áudio
            else:
                #print("Aqui->" + str(current_size) + ' - ' + str(filesize) + ' - ' + str(int(filesize) % CHUNK))
                if(filesize % CHUNK > CHUNK/4):
                    content = clientSocket.recv(filesize % CHUNK)
                    stream.write(content)  # "Player" de áudio
                break
            
        print("Audio executado")

        stream.close()
        p.terminate()
    else:
        break

clientSocket.close() 
