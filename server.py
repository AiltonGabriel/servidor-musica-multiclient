# AUDIOserver3.py
# coding: utf-8

import socket
import wave
import threading
import pickle
import time
import glob

CHUNK = 1024                     # Número de frames de áudio
MUSIC_EXTENSION = '.wav'         # Extensão das músicas.
MUSICS_FOLDER = 'musicas/'       # Diretório que contém as músicas do servidor.

MUSIC_LIST_SERVER_PORT = 13000   # Porta do servidor responsável por transmitir a lista de músicas disnponíveis.
MUSIC_SERVER_PORT = 12000        # Porta do servidor responsável por transmitir as músicas.


#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Servidor da lista de músicas - Lê os dados e as músicas diponíveis para a aplicação do disco e às envia para o cliente.

# Aguarda uma conexão e incia uma thread para servir o cliente conectado.
def music_list_server():
    music_list_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    music_list_server_socket.bind(('', MUSIC_LIST_SERVER_PORT))
    music_list_server_socket.listen(0)
    while True:
        connectionSocket, addr = music_list_server_socket.accept()
        print("\nLista de músicas solicitada por -> {}".format(addr))

        th = threading.Thread(target=connection_music_list, args=(connectionSocket, addr))
        th.start()

# Lê do disco e envia a lista de músicas diponíveis para o cliente.
def connection_music_list(connectionSocket, addr):
    subdirs = glob.glob( MUSICS_FOLDER + "*/")                           # Obtendo os subdiretórios que representam cada artista.
    music_list = []
    for subdir in subdirs:
        # Extraindo o nome do artista do caminho do subdiretório.
        artist = subdir[:len(subdir)-1]
        artist = artist[artist.rindex("\\") + 1:]
        
        musics =  glob.glob(subdir + '*' + MUSIC_EXTENSION)              # Obtendo as músicas desse artista.
        for music in musics:
            music = music[music.rindex("\\") + 1:music.rindex(".")]      # Extraindo o nome da música do caminho.
            music_list.append({'title': music, 'artist': artist})        # Adicionando música à lista.

    data_string = pickle.dumps(music_list)
    connectionSocket.send(data_string)

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Servidor de músicas - Realiza o streaming das músicas.

# Aguarda uma conexão e incia uma thread para servir o cliente conectado.
def music_server():
    music_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    music_server_socket.bind(('', MUSIC_SERVER_PORT))
    music_server_socket.listen(0)
    while True:
        connectionSocket, addr = music_server_socket.accept()
        print("\nMúsica solicitada por -> {}".format(addr))

        th = threading.Thread(target=connection_music, args=(connectionSocket, addr))
        th.start()

# Recebe a solicitação de uma música do cliente e realiza o streaming dela caso à encontre. 
# Obs: Uma música por conexão, caso não encontre a música solicitada simplesmente encerra a conexão.
def connection_music(connectionSocket, addr):

    # Caso encontre qualquer problema ou não encontre a música solicitada encerra a conexão.
    try:
        music = pickle.loads(connectionSocket.recv(4096))                # Recebendo a solicitação do cliente.

        if(music):
            # Construindo o caminho da música.
            fname = MUSICS_FOLDER + music['artist'] + '/' + music['title']
            fname = fname.replace('.', '')
            fname += '.wav'

            wf = wave.open(fname, 'rb')                                  # Abrindo o arquivo da música.
            print("Transmitindo música: {} - {}".format(music['artist'], music['title']))
            
            # Transmitindo a música.
            data = wf.readframes(CHUNK)
            while data:                   
                connectionSocket.send(data)
                data = wf.readframes(CHUNK)

            wf.close()                                                   # Fechando o arquivo da música no após a transmissão.
    except:
        pass

    connectionSocket.close()                                             # Encerrando conexão.

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Main - Iniciando os servidores

def main():
    try:
        # Iniciando os sevidores

        # Servidor responsável por fornecer a lista de músicas do servidor.
        th_music_list_server = threading.Thread(target=music_list_server)
        th_music_list_server.daemon = True                               # Utilizado para que não seja necessário esperar essa thread finalizar para que o programa seja encerrado.
        th_music_list_server.start()

        # Servidor responsável pelo streaming de músicas.
        th_music_server = threading.Thread(target=music_server)
        th_music_server.daemon = True                                    # Utilizado para que não seja necessário esperar essa thread finalizar para que o programa seja encerrado.
        th_music_server.start()

        print("Servidor pronto para enviar.")

        # Como as threads filhas foram definidas como daemon é necessário que a thread principal 
        # tenha algo executando, caso contrário chegando à esse ponto o programa simplesmente
        # encerraria e após o encerramento da thread principal as filhas seriam encerradas também.
        while True:
            time.sleep(1)
    except:
        print("\nServidor Encerrado!")
                	
if __name__ == '__main__':
	main()