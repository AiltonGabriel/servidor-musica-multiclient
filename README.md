# servidor-musica-multiclient

## _Servidor de Músicas Multicliente_
O Servidor de Músicas Multicliente  foi desenvolvido pelos alunos _Ailton Gabriel de Oliveira_ e _Márcio de Amorim Oliveira Filho_ como trabalho prático da disciplina _Redes de Computadores_ da graduação em _Sistemas para Internet_ no [IF SUDESTE MG - Campus Barbacena](https://www.ifsudestemg.edu.br/barbacena). Este programa foi feito em [Python](https://www.python.org/) e consiste em um de servidor e um cliente que se comunicam através de sockets TCP que utilizam criptografia SSL, onde o servidor envia músicas para o cliente e ele às reproduz enquanto recebe, realizando assim um streaming de músicas.

## Dependências
É recomendável o uso do Conda, que pode ser encontrado no site: [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

Crie um ambiente virtual no Conda utilizando o Python na versão 3.6 (é indicado que não seja utilizado uma versão mais recente pois pode acarretar erros na instalação do [PyAudio](https://pypi.org/project/PyAudio/)):
```
conda create --name myenv python=3.6
```

Instale o pip caso não tenha:
```
conda install pip
```

Instale o [PyAudio](https://pypi.org/project/PyAudio/):
```
pip install PyAudio
```

Caso não consiga instalar utilizando o pip, também é possivel instalar utilizando o Conda:
```
conda install PyAudio
```

Instale o PyQt5:
```
pip install PyQt5
```

## Utilização

1. Faça o download do programa e extraia em uma pasta.
2. Execute o servidor:
    ```
    python server.py
    ```
2. Execute o cliente:
    ```
    python client.py
    ```