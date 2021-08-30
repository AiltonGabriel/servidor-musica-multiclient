from PyQt5 import QtCore, QtGui, QtWidgets
from os import environ
from Music import Music
import socket
import pyaudio
import pickle
import random
import threading
import time
import re
import ssl

SERVER_NAME = '127.0.0.1'
MUSIC_SERVER_PORT = 12000
MUSIC_LIST_SERVER_PORT = 13000

CA_CERT = 'ssl/cacert.pem'

# Parâmetros para a reprodução das músicas.
FORMAT = 8
CHANNELS = 2
RATE = 44100
CHUNK = 2048

# Usadas na GUI.
TAMANHO_ICONES = 15
MUSIC_ROLE = QtCore.Qt.UserRole + 1

def get_music_list(ip):
    music_list = []
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Configurando o SSL.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(CA_CERT)
    client_socket_ssl = context.wrap_socket(client_socket, server_hostname=ip)

    client_socket_ssl.connect((ip, MUSIC_LIST_SERVER_PORT))
    music_list = pickle.loads(client_socket_ssl.recv(4096))
    client_socket_ssl.close()

    return music_list

def validar_ip(ip):
    valid_format = re.search("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)

    if(valid_format):
        for o in ip.split("."):
            if(int(o) < 0 or int(o) > 255):
                return False
        return True
    else:
        return False

# Thread responsável por solicitar as músicas da playlist para o servidor e as reproduzir.
class Player(threading.Thread):
    
    skip = False                            # Indica se o usuário solicitou que a música atual seja pulada.
    paused = False                          # Indica se o player está pausado.              

    def __init__(self, ui, *args, **kwargs):
        super(Player, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()     # Utilizado para pausar a thread.
        self.__flag.set()
        self.__running = threading.Event()  # Usado para para a thread.
        self.__running.set()
        self.ui = ui                        # A UI que contém este player, usado para pegar as músicas da playlist e gerenciar a parte gráfica do player.

    def run(self):
        # Executa em loop até que o flag de stop seja setado.
        while self.__running.isSet():
            # Aguarda o flag de pause ser liberado, caso não esteja pausado simplesmente passa direto.
            self.__flag.wait()

            # Verificando se existe alguma música na playlist.
            if(self.ui.lista_reproducao_listWidget.count() > 0):
                
                # Tentando abrir a conexão com o servidor.
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                    # Configurando o SSL.
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    context.load_verify_locations(CA_CERT)
                    client_socket_ssl = context.wrap_socket(client_socket, server_hostname=SERVER_NAME)

                    client_socket_ssl.connect((SERVER_NAME, MUSIC_SERVER_PORT))
                except:
                    client_socket_ssl = None

                # Caso consiga abrir a conexão iniciando o streaming da música.
                if(client_socket_ssl):
                    # Obtendo a música da playlist.
                    music = self.ui.lista_reproducao_listWidget.item(0).data(MUSIC_ROLE)

                    # Informando para retirar a música da playlist e colocar no player da GUI.
                    self.ui.next_music_flag = True
                    self.ui.reset_progress_time_counter_flag = True

                    # Enviando a solicitação da música desejada para o servidor.
                    data_string = pickle.dumps(music)
                    client_socket_ssl.send(data_string)

                    # Criando e configurando o pyaudio.
                    p = pyaudio.PyAudio()
                    stream = p.open(format=FORMAT,
                                    channels=CHANNELS,
                                    rate=RATE,
                                    output=True,
                                    frames_per_buffer=CHUNK)

                    self.ui.play_flag = True

                    # Recebendo e reproduzindo a música.
                    content = client_socket_ssl.recv(CHUNK)
                    if content:                     # Caso a conexão já tenha sido encerrada e não receba nenhum pacote quer dizer que o servidor não contém a música solicitada. 
                        while content and not self.skip:
                            self.__flag.wait()      # Aguardando caso seja pausada.
                            stream.write(content)
                            content = client_socket_ssl.recv(CHUNK)
                    else:
                        self.ui.pausar_flag = True
                        self.ui.music_unavailable_flag = True
                        time.sleep(3)

                    # Liberando pyaudio e fechando a conexão ao final da reprodução.
                    stream.close()
                    p.terminate()
                    client_socket_ssl.close()
                    self.skip = False
                else:   # Servidor indisponível.
                    self.ui.reset_progress_time_counter_flag = True
                    self.ui.pausar_flag = True
                    self.ui.unreacheable_server_flag = True
                    
            else:   # Playlist não contém mais músicas.
                self.pause()
                self.ui.reset_progress_time_counter_flag = True

    # Retorna se o player está pausado.
    def isPaused(self):
        return self.paused
    
    # Para a música atual e reproduz a próxima caso tenha.
    def skipMusic(self):
        self.skip = True

    # Pausa o player
    def pause(self):
        self.paused = True
        self.__flag.clear()                                 # Bloqueia a thread.
        self.ui.pausar_flag = True

    # Resume o player.
    def resume(self):
        self.paused = False
        self.__flag.set()                                   # Desbloqueia thread.
        self.ui.play_flag = True

    # Para o player.
    def stop(self):
        self.skip = True
        self.__flag.set()                                   # Resume a thread caso esteja pausada.
        self.__running.clear()                              # Indica para sair do loop principal e terminar a execução da thread.
        self.ui.reset_progress_time_counter_flag = True     # Indica para resetar as informações do player na GUI.

# GUI
class Ui_MainWindow(object):
    music_list = []
    player = None

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(750, 450)
        MainWindow.setMinimumSize(QtCore.QSize(600, 400))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.musicas_disponiveis_groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.musicas_disponiveis_groupBox.setObjectName("musicas_disponiveis_groupBox")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.musicas_disponiveis_groupBox)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.filtrar_artista_widgetwidget = QtWidgets.QWidget(self.musicas_disponiveis_groupBox)
        self.filtrar_artista_widgetwidget.setMinimumSize(QtCore.QSize(0, 40))
        self.filtrar_artista_widgetwidget.setObjectName("filtrar_artista_widgetwidget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.filtrar_artista_widgetwidget)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.filtrar_artista_label = QtWidgets.QLabel(self.filtrar_artista_widgetwidget)
        self.filtrar_artista_label.setMaximumSize(QtCore.QSize(65, 16777215))
        self.filtrar_artista_label.setObjectName("filtrar_artista_label")
        self.horizontalLayout_2.addWidget(self.filtrar_artista_label)
        self.filtrar_artista_comboBox = QtWidgets.QComboBox(self.filtrar_artista_widgetwidget)
        self.filtrar_artista_comboBox.setObjectName("filtrar_artista_comboBox")
        self.filtrar_artista_comboBox.addItem("")
        self.filtrar_artista_comboBox.currentTextChanged.connect(self.filter_artist)
        self.horizontalLayout_2.addWidget(self.filtrar_artista_comboBox)
        self.verticalLayout_4.addWidget(self.filtrar_artista_widgetwidget)
        self.musicas_disponiveis_listWidget = QtWidgets.QListWidget(self.musicas_disponiveis_groupBox)
        self.musicas_disponiveis_listWidget.setStyleSheet("QListView{\n"
                                                        "    outline: 0;\n"
                                                        "}\n"
                                                        "QListView::item:selected{\n"
                                                        "    color: rgb(0, 0, 0);\n"
                                                        "    background-color: rgba(0, 170, 221, 0.3);\n"
                                                        "}\n"
                                                        "QListView::item:hover{\n"
                                                        "    background-color: rgba(0, 170, 221, 0.2);\n"
                                                        "}")
        self.musicas_disponiveis_listWidget.setObjectName("musicas_disponiveis_listWidget")
        self.verticalLayout_4.addWidget(self.musicas_disponiveis_listWidget)

        self.erroServerLabel = QtWidgets.QLabel(self.musicas_disponiveis_groupBox)
        self.erroServerLabel.setMinimumSize(QtCore.QSize(0, 30))
        self.erroServerLabel.setStyleSheet("QLabel{\n"
        "    background-color: rgba(255,0,0,0.6);\n"
        "    color: white;\n"
        "}")
        self.erroServerLabel.setText("")
        self.erroServerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.erroServerLabel.setObjectName("erroServerLabel")
        self.erroServerLabel.setVisible(False)
        self.verticalLayout_4.addWidget(self.erroServerLabel)
        self.ipWidget = QtWidgets.QWidget(self.musicas_disponiveis_groupBox)
        self.ipWidget.setObjectName("ipWidget")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.ipWidget)
        self.horizontalLayout_5.setContentsMargins(0, -1, 0, -1)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.ipLabel = QtWidgets.QLabel(self.ipWidget)
        self.ipLabel.setObjectName("ipLabel")
        self.horizontalLayout_5.addWidget(self.ipLabel)
        self.ipLineEdit = QtWidgets.QLineEdit(self.ipWidget)
        self.ipLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.ipLineEdit.setObjectName("ipLineEdit")
        self.horizontalLayout_5.addWidget(self.ipLineEdit)
        self.verticalLayout_4.addWidget(self.ipWidget)

        self.atualizar_lista_pushButton = QtWidgets.QPushButton(self.musicas_disponiveis_groupBox, clicked= self.update_music_list)
        self.atualizar_lista_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.atualizar_lista_pushButton.setObjectName("atualizar_lista_pushButton")
        self.verticalLayout_4.addWidget(self.atualizar_lista_pushButton)
        self.horizontalLayout.addWidget(self.musicas_disponiveis_groupBox)
        self.acoes_widget = QtWidgets.QWidget(self.centralwidget)
        self.acoes_widget.setMinimumSize(QtCore.QSize(150, 0))
        self.acoes_widget.setMaximumSize(QtCore.QSize(100, 300))
        self.acoes_widget.setBaseSize(QtCore.QSize(90, 0))
        self.acoes_widget.setObjectName("acoes_widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.acoes_widget)
        self.verticalLayout.setContentsMargins(0, -1, 0, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.adicionar_widget = QtWidgets.QWidget(self.acoes_widget)
        self.adicionar_widget.setMaximumSize(QtCore.QSize(16777215, 100))
        self.adicionar_widget.setObjectName("adicionar_widget")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.adicionar_widget)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.adicionar_pushButton = QtWidgets.QPushButton(self.adicionar_widget, clicked= self.add_music_playlist)
        self.adicionar_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.adicionar_pushButton.setObjectName("adicionar_pushButton")
        self.verticalLayout_5.addWidget(self.adicionar_pushButton)
        self.aleatorio_pushButton = QtWidgets.QPushButton(self.adicionar_widget, clicked=self.random_playlist)
        self.aleatorio_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.aleatorio_pushButton.setObjectName("aleatorio_pushButton")
        self.verticalLayout_5.addWidget(self.aleatorio_pushButton)
        self.verticalLayout.addWidget(self.adicionar_widget)

        self.reordenar_widget = QtWidgets.QWidget(self.acoes_widget)
        self.reordenar_widget.setMaximumSize(QtCore.QSize(16777215, 100))
        self.reordenar_widget.setObjectName("reordenar_widget")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.reordenar_widget)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.music_up_playlist_pushButton = QtWidgets.QPushButton(self.reordenar_widget, clicked= self.music_up_playlist)
        self.music_up_playlist_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.music_up_playlist_pushButton.setObjectName("music_up_playlist_pushButton")
        self.verticalLayout_7.addWidget(self.music_up_playlist_pushButton)
        self.music_down_playlist_pushButton = QtWidgets.QPushButton(self.reordenar_widget, clicked=self.music_down_playlist)
        self.music_down_playlist_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.music_down_playlist_pushButton.setObjectName("music_down_playlist_pushButton")
        self.verticalLayout_7.addWidget(self.music_down_playlist_pushButton)
        self.verticalLayout.addWidget(self.reordenar_widget)

        self.remover_widget = QtWidgets.QWidget(self.acoes_widget)
        self.remover_widget.setMaximumSize(QtCore.QSize(16777215, 100))
        self.remover_widget.setObjectName("remover_widget")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.remover_widget)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.remover_pushButton = QtWidgets.QPushButton(self.remover_widget, clicked=self.remove_music_playlist)
        self.remover_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.remover_pushButton.setObjectName("remover_pushButton")
        self.verticalLayout_6.addWidget(self.remover_pushButton)
        self.remover_todas_pushButton = QtWidgets.QPushButton(self.remover_widget, clicked=self.remove_all_music_playlist)
        self.remover_todas_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.remover_todas_pushButton.setObjectName("remover_todas_pushButton")
        self.verticalLayout_6.addWidget(self.remover_todas_pushButton)
        self.verticalLayout.addWidget(self.remover_widget)
        self.horizontalLayout.addWidget(self.acoes_widget, 0, QtCore.Qt.AlignHCenter)
        self.lista_reproducao_groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.lista_reproducao_groupBox.setObjectName("lista_reproducao_groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.lista_reproducao_groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lista_reproducao_listWidget = QtWidgets.QListWidget(self.lista_reproducao_groupBox)
        self.lista_reproducao_listWidget.setEnabled(True)
        self.lista_reproducao_listWidget.setStyleSheet("QListView{\n"
                                                        "    outline: 0;\n"
                                                        "}\n"
                                                        "QListView::item:selected{\n"
                                                        "    color: rgb(0, 0, 0);\n"
                                                        "    background-color: rgba(0, 170, 221, 0.3);\n"
                                                        "}\n"
                                                        "QListView::item:hover{\n"
                                                        "    background-color: rgba(0, 170, 221, 0.2);\n"
                                                        "}")
        self.lista_reproducao_listWidget.setObjectName("lista_reproducao_listWidget")
        self.verticalLayout_2.addWidget(self.lista_reproducao_listWidget)
        self.player_widget = QtWidgets.QWidget(self.lista_reproducao_groupBox)
        self.player_widget.setMinimumSize(QtCore.QSize(0, 60))
        self.player_widget.setObjectName("player_widget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.player_widget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.musica_label = QtWidgets.QLabel(self.player_widget)
        self.musica_label.setAlignment(QtCore.Qt.AlignCenter)
        self.musica_label.setObjectName("musica_label")
        self.musica_label.setWordWrap(True)
        self.verticalLayout_3.addWidget(self.musica_label)
        self.progresso_widget = QtWidgets.QWidget(self.player_widget)
        self.progresso_widget.setMinimumSize(QtCore.QSize(0, 30))
        self.progresso_widget.setObjectName("progresso_widget")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.progresso_widget)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.tempo_reproduzido_label = QtWidgets.QLabel(self.progresso_widget)
        self.tempo_reproduzido_label.setObjectName("tempo_reproduzido_label")

        # Atributos da parte GUI do player.
        self.music_total_time = 0
        self.music_played_time = 0
        self.music_played_time_start = time.time()
        self.music_played_time_end = time.time()
        self.progress_time_flag = False
        # Chama uma função responsável pela atualização do tempo de reprodução da música de tempo em tempo (aproximadamente à cada 1/10 de segundo, porém não é muito preciso).
        self.timer = QtCore.QTimer(self.progresso_widget)
        self.timer.timeout.connect(self.showTime)
        self.timer.start(0)
        
        self.horizontalLayout_3.addWidget(self.tempo_reproduzido_label)
        self.progresso_progressBar = QtWidgets.QProgressBar(self.progresso_widget)
        self.progresso_progressBar.setEnabled(True)
        self.progresso_progressBar.setMinimumSize(QtCore.QSize(0, 13))
        self.progresso_progressBar.setMaximumSize(QtCore.QSize(16777215, 13))
        self.progresso_progressBar.setStyleSheet("QProgressBar{\n"
                                                "    border-radius: 20px;\n"
                                                "    background-color: #dddddd;\n"
                                                "    color: transparent;\n"
                                                "}\n"
                                                "QProgressBar::chunk \n"
                                                "{\n"
                                                "    background-color: #00aadd;\n"
                                                "    border-radius :20px;\n"
                                                "}")
        self.progresso_progressBar.setProperty("value", 0)
        self.progresso_progressBar.setAlignment(QtCore.Qt.AlignCenter)
        self.progresso_progressBar.setTextVisible(True)
        self.progresso_progressBar.setInvertedAppearance(False)
        self.progresso_progressBar.setObjectName("progresso_progressBar")
        self.horizontalLayout_3.addWidget(self.progresso_progressBar)
        self.duracao_label = QtWidgets.QLabel(self.progresso_widget)
        self.duracao_label.setObjectName("duracao_label")
        self.horizontalLayout_3.addWidget(self.duracao_label)
        self.verticalLayout_3.addWidget(self.progresso_widget)
        self.acoes_player_widget = QtWidgets.QWidget(self.player_widget)
        self.acoes_player_widget.setMinimumSize(QtCore.QSize(0, 30))
        self.acoes_player_widget.setObjectName("acoes_player_widget")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.acoes_player_widget)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.pausar_pushButton = QtWidgets.QPushButton(self.acoes_player_widget, clicked=self.pausar)
        self.pausar_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.pausar_pushButton.setObjectName("pausar_pushButton")
        self.horizontalLayout_4.addWidget(self.pausar_pushButton)
        self.proxima_pushButton = QtWidgets.QPushButton(self.acoes_player_widget, clicked=self.skip_stop_music)
        self.proxima_pushButton.setMinimumSize(QtCore.QSize(0, 30))
        self.proxima_pushButton.setObjectName("proxima_pushButton")
        self.horizontalLayout_4.addWidget(self.proxima_pushButton)
        self.verticalLayout_3.addWidget(self.acoes_player_widget)
        self.verticalLayout_2.addWidget(self.player_widget)
        self.horizontalLayout.addWidget(self.lista_reproducao_groupBox)
        MainWindow.setCentralWidget(self.centralwidget)

        # Setando os ícones.

        MainWindow.setWindowIcon(QtGui.QIcon('icons/icon.png'))

        self.atualizar_lista_pushButton.setIcon(QtGui.QIcon('icons/update.png'))
        self.atualizar_lista_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))

        self.adicionar_pushButton.setIcon(QtGui.QIcon('icons/add.png'))
        self.adicionar_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.aleatorio_pushButton.setIcon(QtGui.QIcon('icons/random.png'))
        self.adicionar_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.music_up_playlist_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_TitleBarShadeButton")))
        self.music_up_playlist_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.music_down_playlist_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_TitleBarUnshadeButton")))
        self.music_down_playlist_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.remover_pushButton.setIcon(QtGui.QIcon('icons/remove.png'))
        self.adicionar_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.remover_todas_pushButton.setIcon(QtGui.QIcon('icons/remove_all.png'))
        self.adicionar_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))

        self.pausar_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_MediaPause")))
        self.pausar_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))
        self.proxima_pushButton.setIcon(self.proxima_pushButton.style().standardIcon(getattr(QtWidgets.QStyle,"SP_MediaStop")))
        self.proxima_pushButton.setIconSize(QtCore.QSize(TAMANHO_ICONES, TAMANHO_ICONES))

        self.retranslateUi(MainWindow)
        self.musicas_disponiveis_listWidget.setCurrentRow(-1)
        self.lista_reproducao_listWidget.setCurrentRow(-1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Flags utilizas nas interações entre a thread do player e a GUI.
        self.next_music_flag = False
        self.reset_progress_time_counter_flag = True
        self.play_flag = False
        self.pausar_flag = True
        self.music_unavailable_flag = False
        self.unreacheable_server_flag = False
        # Executa a aproximadamente 1/10 de segundo executando modificações na GUI solicitadas pela thread do player.
        self.timer = QtCore.QTimer(self.centralwidget)
        self.timer.timeout.connect(self.player_interactions_listener)
        self.timer.start(0)

        # Criando e startando a thread do player.
        self.player = Player(ui=self)
        # Utilizado para que não seja necessário esperar essa thread finalizar para que o programa seja encerrado. 
        # Obs: Quando a thead princial é finalizada as filhas são finalizadas também, 
        # o deamon só é utilizado para que a thread filha não bloqueie o encerramento da principal.
        self.player.daemon = True
        self.player.start()

        self.update_music_list()                # Pedindo a lista de músicas para o servidor e preenchendo a listagem no GUI.        
        self.fill_player_info(music=None)       # Resetando os dados do player no GUI.

    # Solicia a lista de músicas ao servidor e preenche a listagem de músicas disponíveis.
    def update_music_list(self):
        try:
            ip = self.ipLineEdit.text()
            if(validar_ip(ip)):
                music_list = get_music_list(ip)
                music_list.sort(key=lambda music: music.title.lower())

                self.music_list = music_list
                self.update_filtrar_artista_comboBox()

                self.musicas_disponiveis_listWidget.clear()
                for music in music_list:
                    item = QtWidgets.QListWidgetItem(repr(music))
                    self.musicas_disponiveis_listWidget.addItem(item)
                    item.setData(MUSIC_ROLE, music)

                if(self.musicas_disponiveis_listWidget.count() > 0):
                    self.musicas_disponiveis_listWidget.setCurrentRow(0)

                self.erroServerLabel.hide()
            else:
                self.erroServerLabel.setText("Erro! IP do servidor inválido!")
                self.erroServerLabel.show()
        except:
            self.musicas_disponiveis_listWidget.clear()
            self.erroServerLabel.setText("Erro! Servidor indisponível!")
            self.erroServerLabel.show()
            
    # Atualiza a combobox de seleção de artistas com os artistas das músicas disponíveis.
    def update_filtrar_artista_comboBox(self):
        self.filtrar_artista_comboBox.clear()
        artists = []
        for music in self.music_list:
            if music.artist not in artists:
                artists.append(music.artist)
        artists.sort()
        self.filtrar_artista_comboBox.addItems(artists)
        self.filtrar_artista_comboBox.insertItem(0, 'Todos')
        self.filtrar_artista_comboBox.setCurrentIndex(0)

    # Preenche a listagem de músicas disponíveis com somente as músicas do artista selecionado.
    def filter_artist(self):
        artist = self.filtrar_artista_comboBox.currentText()
        
        self.musicas_disponiveis_listWidget.clear()
        for music in self.music_list:
            if artist == 'Todos' or music.artist == artist:
                item = QtWidgets.QListWidgetItem(repr(music))
                self.musicas_disponiveis_listWidget.addItem(item)
                item.setData(MUSIC_ROLE, music)

        if(self.musicas_disponiveis_listWidget.count() > 0):
            self.musicas_disponiveis_listWidget.setCurrentRow(0)

    # Adiciona a música selecionada ao final da playlist.
    def add_music_playlist(self):
        if(self.musicas_disponiveis_listWidget.currentRow() >= 0):
            selected_item = self.musicas_disponiveis_listWidget.currentItem()
            item = QtWidgets.QListWidgetItem(selected_item)
            self.lista_reproducao_listWidget.addItem(item)
            self.update_buttons()
            if(self.player.isPaused() and not self.pausar_pushButton.isEnabled()):
                self.player.resume()

    # Adiciona todas as músicas da listagem na playlist de forma aleatória.
    def random_playlist(self):
        if(self.musicas_disponiveis_listWidget.isEnabled()):
            playlist = []
            for row in range(self.musicas_disponiveis_listWidget.count()):
                playlist.append(self.musicas_disponiveis_listWidget.item(row).data(MUSIC_ROLE))
            
            random.shuffle(playlist)

            for music in playlist:
                item = QtWidgets.QListWidgetItem(repr(music))
                self.lista_reproducao_listWidget.addItem(item)
                item.setData(MUSIC_ROLE, music)
            self.update_buttons()
            if(self.player.isPaused()):
                self.player.resume()

    # Sobe a posição de uma música na playlist.
    def music_up_playlist(self):
        selected_index = self.lista_reproducao_listWidget.currentRow()
        if(selected_index > 0):
            selected_item = self.lista_reproducao_listWidget.takeItem(selected_index)
            item = QtWidgets.QListWidgetItem(selected_item)
            self.lista_reproducao_listWidget.insertItem(selected_index - 1, item)
            self.lista_reproducao_listWidget.setCurrentRow(selected_index - 1)

    # Abaixa a posição de uma música na playlist.
    def music_down_playlist(self):
        selected_index = self.lista_reproducao_listWidget.currentRow()
        if(selected_index >= 0 and selected_index < self.lista_reproducao_listWidget.count()-1):
            selected_item = self.lista_reproducao_listWidget.takeItem(selected_index)
            item = QtWidgets.QListWidgetItem(selected_item)
            self.lista_reproducao_listWidget.insertItem(selected_index + 1, item)
            self.lista_reproducao_listWidget.setCurrentRow(selected_index + 1)

    # Remove a música selecionada da playlist.
    def remove_music_playlist(self):
        selected_index = self.lista_reproducao_listWidget.currentRow()
        self.lista_reproducao_listWidget.takeItem(selected_index)
        self.update_buttons()

    # Remove todas as músicas da playlist.
    def remove_all_music_playlist(self):
        selected_index = self.lista_reproducao_listWidget.clear()
        self.update_buttons()

    # Pausa a reprodução de uma música.
    def pausar(self):
        if(self.player.isPaused()):
            self.player.resume()
        else:
            self.player.pause()

    # Para a reprodução da música atual e pula para a próxima caso tenha.
    def skip_stop_music(self):
        self.player.skipMusic()
        if(self.player.isPaused()):
            self.player.resume()
        
    # Executa modificações na GUI solicitadas pela thread do player.
    def player_interactions_listener(self):
        music = None
        #  Preenche os dados da próxima música no player da GUI e à retira da playlist.
        if(self.next_music_flag == True):
            music = self.lista_reproducao_listWidget.item(0).data(MUSIC_ROLE)
            self.lista_reproducao_listWidget.takeItem(0)
            self.next_music_flag = False

        # Reseta o player da GUI com os dados da próxima música caso tenha ou limpa o player da GUI caso não tenha.
        if(self.reset_progress_time_counter_flag == True):
            self.resetProgressTimeCounter(music)
            self.reset_progress_time_counter_flag = False

        # Pausa o player da GUI.
        if(self.pausar_flag == True):
            self.pauseProgressTimeCounter()
            self.update_buttons()
            self.pausar_flag = False

        # Inicia ou resume o player da GUI.
        if(self.play_flag == True):
            self.startProgressTimeCounter()
            self.update_buttons()
            self.play_flag = False

        # Exibe a mensagem que o servidor não conté esta música.
        if(self.music_unavailable_flag == True):
            self.musica_label.setText("Erro! O servidor não contém mais a música:\n" + self.musica_label.text())
            self.pausar_pushButton.setEnabled(False)
            self.proxima_pushButton.setEnabled(False)
            self.music_unavailable_flag = False

        # Exbibe a mensagem caso não consiga se conectar ao servidor.
        if(self.unreacheable_server_flag == True):
            self.musica_label.setText("Erro! O servidor não está respondendo!")
            self.unreacheable_server_flag = False

    # Atualiza as informações do tempo de reprodução da música de tempo em tempo.
    def showTime(self):
        if self.progress_time_flag:

            self.music_played_time_end  = time.time()
            #self.music_played_time += self.music_played_time_end - self.music_played_time_start
            #self.music_played_time_start  = time.time()

            music_played_time = self.music_played_time + self.music_played_time_end - self.music_played_time_start
            
            text_time_passed = "{:02d}:{:02d}".format(int(music_played_time / 60.0), int(music_played_time % 60.0))

            self.tempo_reproduzido_label.setText(text_time_passed)
            self.progresso_progressBar.setValue(int(music_played_time))
  
    # Inicia ou resume a contagem do tempo de reprodução da música.
    def startProgressTimeCounter(self):        
        self.music_played_time_start = time.time()
        self.progress_time_flag = True
  
    # Pausa a contagem do tempo de reprodução da música.
    def pauseProgressTimeCounter(self):
        self.music_played_time_end  = time.time()
        self.music_played_time += self.music_played_time_end - self.music_played_time_start
        self.progress_time_flag = False
  
    # Reseta a contagem do tempo de reprodução da música.
    def resetProgressTimeCounter(self, music=None):
        self.fill_player_info(music=music)
        self.progress_time_flag = False

    # Atualiza o texto dos botões de acordo com o estado dos componentes e do player.
    def update_buttons(self):
        if(self.player.isPaused()):
            self.pausar_pushButton.setText("Retomar")
            self.pausar_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_MediaPlay")))
        else:
            self.pausar_pushButton.setText("Pausar")
            self.pausar_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_MediaPause")))

        if(self.lista_reproducao_listWidget.count() > 0):
            self.proxima_pushButton.setText("Próxima")
            self.proxima_pushButton.setIcon(self.proxima_pushButton.style().standardIcon(getattr(QtWidgets.QStyle,"SP_MediaSkipForward")))
            self.remover_pushButton.setEnabled(True)
            self.remover_todas_pushButton.setEnabled(True)
        else:
            self.proxima_pushButton.setText("Parar")
            self.proxima_pushButton.setIcon(self.proxima_pushButton.style().standardIcon(getattr(QtWidgets.QStyle,"SP_MediaStop")))
            self.remover_pushButton.setEnabled(False)
            self.remover_todas_pushButton.setEnabled(False)
        
        if(self.lista_reproducao_listWidget.count() > 1):
            self.music_up_playlist_pushButton.setEnabled(True)
            self.music_down_playlist_pushButton.setEnabled(True)
        else:
            self.music_up_playlist_pushButton.setEnabled(False)
            self.music_down_playlist_pushButton.setEnabled(False)

    # Preenche os campos da plarte GUI do player com os dados da música ou reseta caso a música não seja passada.
    def fill_player_info(self, music=None):
        self.update_buttons()
        if(music):
            self.adicionar_pushButton.setText("Adicionar")
            self.musica_label.setText(str(music))
            self.pausar_pushButton.setEnabled(True)
            self.proxima_pushButton.setEnabled(True)
            self.music_total_time = music.duration

        elif(not self.lista_reproducao_listWidget.count() > 0):
            self.adicionar_pushButton.setText("Reproduzir")
            self.musica_label.setText("")
            self.pausar_pushButton.setEnabled(False)
            self.proxima_pushButton.setEnabled(False)
            self.pausar_pushButton.setText("Pausar")
            self.pausar_pushButton.setIcon(self.pausar_pushButton.style().standardIcon(getattr(QtWidgets.QStyle, "SP_MediaPause")))
            self.music_total_time = 0
        
        self.music_played_time = 0
        if self.music_total_time > 0:
            self.progresso_progressBar.setRange(0, int(self.music_total_time))
        else:
            self.progresso_progressBar.setRange(0, 100)

        text_time_passed = "{:02d}:{:02d}".format(int(self.music_played_time / 60.0), int(self.music_played_time % 60.0))
        text_music_total_time = "{:02d}:{:02d}".format(int(self.music_total_time / 60.0), int(self.music_total_time % 60.0))

        self.tempo_reproduzido_label.setText(text_time_passed)
        self.duracao_label.setText(text_music_total_time)
        self.progresso_progressBar.setValue(0)
            
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Cliente de Músicas"))
        self.musicas_disponiveis_groupBox.setTitle(_translate("MainWindow", "Músicas Disponíveis"))
        self.filtrar_artista_label.setText(_translate("MainWindow", "Filtrar artista: "))
        self.filtrar_artista_comboBox.setToolTip(_translate("MainWindow", "Filtra as músicas disponíveis pelo artista."))
        self.filtrar_artista_comboBox.setItemText(0, _translate("MainWindow", "Todos"))
        self.ipLabel.setText(_translate("MainWindow", "IP do Servidor:"))
        self.ipLineEdit.setText(_translate("MainWindow", "127.0.0.1"))
        self.ipLineEdit.setToolTip(_translate("MainWindow", "Insira o IP do servidor."))
        self.atualizar_lista_pushButton.setText(_translate("MainWindow", "Atualizar Lista"))
        self.atualizar_lista_pushButton.setToolTip(_translate("MainWindow", "Solicita novamente a lista de músicas disponíveis."))
        self.adicionar_pushButton.setText(_translate("MainWindow", "Adicionar"))
        self.adicionar_pushButton.setToolTip(_translate("MainWindow", "Adiciona a música selecionada à lista de reprodução."))
        self.aleatorio_pushButton.setText(_translate("MainWindow", "Aleatório"))
        self.aleatorio_pushButton.setToolTip(_translate("MainWindow", "Adiciona todas as músicas da lista de forma aleatória à lista de reprodução."))
        self.music_up_playlist_pushButton.setToolTip(_translate("MainWindow", "Sobe a posição da música selecionada na fila de reprodução da playlist."))
        self.music_down_playlist_pushButton.setToolTip(_translate("MainWindow", "Abaixa a posição da música selecionada na fila de reprodução da playlist."))
        self.remover_pushButton.setText(_translate("MainWindow", "Remover"))
        self.remover_pushButton.setToolTip(_translate("MainWindow", "Remove a música selecionada da lista de reprodução."))
        self.remover_todas_pushButton.setText(_translate("MainWindow", "Remover Todas"))
        self.remover_todas_pushButton.setToolTip(_translate("MainWindow", "Remove todas as músicas da lista de reprodução."))
        self.lista_reproducao_groupBox.setTitle(_translate("MainWindow", "Lista de Reprodução"))
        self.musica_label.setText(_translate("MainWindow", ""))
        self.tempo_reproduzido_label.setText(_translate("MainWindow", "00:00"))
        self.tempo_reproduzido_label.setToolTip(_translate("MainWindow", "Tempo repoduzido."))
        self.duracao_label.setText(_translate("MainWindow", "00:00"))
        self.duracao_label.setToolTip(_translate("MainWindow", "Tempo total da música."))
        self.progresso_progressBar.setToolTip(_translate("MainWindow", "Quantidade reproduzida da música."))
        self.pausar_pushButton.setText(_translate("MainWindow", "Pausar"))
        self.pausar_pushButton.setToolTip(_translate("MainWindow", "Pausar/Retomar música."))
        self.proxima_pushButton.setText(_translate("MainWindow", "Próxima"))
        self.proxima_pushButton.setToolTip(_translate("MainWindow", "Parar música atual e ir para próxima caso tenha."))

# Estava funcionando normal, porém apresentava algumas warnings estranhas, mesmo com códigos recém gerados pelo designer,
# então copiei esta função de alguém do stackoverflow(perdi o link) e as warnings sumiram.
def suppress_qt_warnings():
    environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    environ["QT_SCALE_FACTOR"] = "1"

if __name__ == "__main__":
    import sys
    suppress_qt_warnings()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
