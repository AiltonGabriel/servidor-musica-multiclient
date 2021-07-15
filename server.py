# AUDIOserver3.py
# coding: utf-8

import socket
import wave
import threading
import pickle
import os
import struct

serverPort = 12000
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(0)

CHUNK = 2048     # Número de frames de áudio

def connection(connectionSocket, addr):

    lista_musicas = (["musica", "Sair"])
    data_string = pickle.dumps(lista_musicas)

    connectionSocket.send(data_string)
    while(True):

        #indiceMusica = connectionSocket.recv(2048)

        musica = struct.unpack("L", connectionSocket.recv(struct.calcsize("L")))[0]

        if(musica != len(lista_musicas) - 1):

            if(musica >= 0 and musica < len(lista_musicas)):
                fname = 'Musicas/' + lista_musicas[musica] + '.wav'
                wf = wave.open(fname, 'rb')

                filesize = os.path.getsize(fname)
                print("Aqui ->" + str(filesize))
                connectionSocket.send(struct.pack("L", filesize))
                
                data = wf.readframes(CHUNK)

                while data:
                    connectionSocket.send(data)
                    data = wf.readframes(CHUNK)
                        
                wf.close()
        else:
            break

    connectionSocket.close()
    


def main():
    print("Servidor pronto para enviar")
    while True:
        connectionSocket, addr = serverSocket.accept()
        print("Conexão vinda de {}".format(addr))

        th = threading.Thread(target=connection, args=(connectionSocket, addr))
        th.start()
                	
if __name__ == '__main__':
	main()