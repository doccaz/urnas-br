#!/usr/bin/python3

from io import BytesIO
import getopt
import os,sys
import pycurl
import json
import pdb

# dados de url
base_url = 'https://resultados.tse.jus.br/oficial/ele2022'

# diretório onde salvar os arquivos
json_dir = 'json/'
data_dir = 'data/'

max_download_speed = 0         # 0 = ilimitado, 512*1024 = 512kbit
max_filesize = 300*1024*1024   # Tamanho maximo de arquivo a ser baixado em bytes (300MB)

connect_timeout = 20    # tempo máximo em segundos para efetuar uma conexão
download_timeout = 20   # tempo máximo sem receber dados para cancelar o download
download_retries = 15   # número de tentativas

ESTADOS= [ 'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms', 'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to' ]

# fixamos o pleito em "406" (eleições gerais 2022) -- ver nota 1
pleito = '406'


# funcao de log
def log(mensagem):
    print(mensagem)
    #syslog.syslog(mensagem)
    return

def exibe_ajuda():
    print('Uso: ')
    print('\t-u|--uf=<estado>\t\tEstado a consultar')
    print('\t-a|--all\t\tBaixa todos os estados')
    print('\t-b|--bu\t\tBaixa apenas os arquivos de BU, ignorando os outros tipos')
    print('\t-h|--help\t\tExibe a ajuda')
    return

# baixa um arquivo
def baixa_arquivo(url, dest_dir, force=False, skipExisting=True):
    status_code = -1
    bytes_size = -1
    fd = None
    filename = os.path.join(dest_dir, os.path.basename(url))
    
    if os.path.exists(filename) and skipExisting:
        log(f"[OK] pulando arquivo {filename} pois já existe e foi solicitado pular")
        return 200, None
    
    try:
        data = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.CONNECTTIMEOUT, connect_timeout)            # timeout para conexao
        c.setopt(pycurl.LOW_SPEED_TIME, download_timeout)           # timeout sem receber dados
        c.setopt(pycurl.MAX_RECV_SPEED_LARGE, max_download_speed)   # velocidade máxima
        c.setopt(pycurl.MAXFILESIZE_LARGE, max_filesize)            # tamanho máximo
        c.setopt(pycurl.VERBOSE, 0)
        c.setopt(c.NOPROGRESS, 1)                                   # desabilita callback de progresso
        c.setopt(pycurl.NOBODY, 1)                                   # apenas busca o tamanho do arquivo (HEAD)
        c.setopt(pycurl.WRITEFUNCTION, lambda x: None)              # para evitar jogar para o terminal o conteúdo
        c.perform()
        status_code = c.getinfo(c.RESPONSE_CODE)
        bytes_size = int(c.getinfo(c.CONTENT_LENGTH_DOWNLOAD))

        c.setopt(pycurl.NOBODY, 0)                              # agora baixamos o arquivo completo
            
        if filename is None:
            c.setopt(c.WRITEFUNCTION, data.write)                   # sem arquivo, voltamos em memória
        else:
            # se o arquivo existir...
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                if (file_size == bytes_size) and force is False:
                    log('[OK] arquivo %s já foi baixado completamente (%d bytes).' % (url, bytes_size))
                    return status_code, None
                     
        fd = open(filename, 'wb')
        c.setopt(c.WRITEFUNCTION, fd.write)
        data = None

        if status_code == 404:
            log('[ERRO] arquivo %s não existe no servidor' % url)
            fd.close()
            os.remove(filename)
            return status_code, None
        
        # faz o download
        log('* iniciando download: %s (%d bytes)' % (url, bytes_size))
        c.perform()
        if fd is not None:
            fd.close()
        total_time = int(c.getinfo(c.TOTAL_TIME))
        c.close()   
        log('[OK] download concluido: %s status: %d (%d bytes, %s segundos)' % (url, status_code, bytes_size, total_time))
            
    except pycurl.error as e:
        if e.args[0] == pycurl.E_COULDNT_CONNECT:
            errmsg = 'erro de conexão'
        if e.args[0] == pycurl.E_FILESIZE_EXCEEDED:
            errmsg = 'tamanho de arquivo remoto excede o máximo permitido.'
        if e.args[0] == pycurl.E_OPERATION_TIMEDOUT:
            errmsg = 'timeout atingido.'
        else:
            errmsg = '[ERRO] ' + str(pycurl.error(e))
        log(errmsg)
        if fd is not None:
            fd.close()
        return -1, errmsg
    except Exception as e:
        errmsg = '[ERRO] ' + str(e)
        if fd is not None:
            fd.close()
        return -1, errmsg
        
    if status_code == 200 and data is not None:
        return status_code, data.getvalue().decode('utf-8')
    else:
        return status_code, None

def processa_estado(filename, somente_bu):
    
    # carrega o arquivo do estado
    with open(filename, "r") as f:
        dados_estado = json.loads(f.read())
        data = dados_estado['abr'][0]
        log(f"total de {len(data['mu'])} municípios para ({data['ds']} - {data['cd']}")
        uf = data['cd'].lower()
        
        # processa municipio por município
        count_mu = 1
        for mu in data['mu']:
            log(f"================= [{count_mu}/{len(data['mu'])}] processando municipio {mu['nm']} ({mu['cd']})")
            count_zona = 1
            for zon in mu['zon']:
                log(f"================= [{count_zona}/{len(mu['zon'])}] processando zona {zon['cd']} ({len(zon['sec'])} seções)")
                count_secao = 1
                for sec in zon['sec']:
                    log(f"================= Município: [{count_mu}/{len(data['mu'])}] Zona: [{count_zona}/{len(mu['zon'])}] Seção: [{count_secao}/{len(zon['sec'])}] processando secao {sec['ns']}")
                    # Obtém lista de urnas por estado/município/seção (com hashes e nomes de arquivos)
                    # https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/p000406-ap-m06050-z0002-s0824-aux.json
                    file = 'p000' + pleito + '-' + uf + '-m' + mu['cd'] + '-z' + zon['cd'] + '-s' + sec['ns'] + '-aux.json' 
                    status, dados_secao = baixa_arquivo(base_url + '/arquivo-urna/' + pleito + '/dados/' + uf + '/' + mu['cd'] + '/' + zon['cd'] + '/' + sec['ns'] + '/' + file, json_dir)
                    if status != 200:
                        log(f"=========> erro {status} ao baixar arquivo de zona, saindo")
                        return False
                    else:
                        # carrega o arquivo da secao
                        with open(os.path.join(json_dir, file), "r") as f:
                            dados_secao = json.loads(f.read())
                        log(f"Total de {len(dados_secao['hashes'])} urnas nesta seção.")

                        # baixa os arquivos individuais de cada urna
                        count_urna = 1
                        for urna in dados_secao['hashes']:
                            log(f"=================  Urna: [{count_urna}/{len(dados_secao['hashes'])}] Baixando arquivos da urna com hash {urna['hash']}")
                            if urna['hash'] == '0':
                                log("Urna não instalada, pulando...")
                                continue
                            
                            for datafile in urna['nmarq']:
                                # baixa os arquivos relacionados a cada urna
                                # https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.logjez
                                outdir = os.path.join(data_dir, uf, mu['cd'], zon['cd'], sec['ns'])
                                os.makedirs(outdir, exist_ok=True)
                                log(f"\t\t---> baixando log de urna: {datafile} para {outdir}")
                                if somente_bu and not os.path.basename(datafile).endswith(".bu"):
                                    log(f"somente BU será baixado, pulando arquivo {datafile}")
                                    continue
                                else:    
                                    status, dados_urna = baixa_arquivo(base_url + '/arquivo-urna/' + pleito + '/dados/' + uf + '/' + mu['cd'] + '/' + zon['cd'] + '/' + sec['ns'] + '/' + urna['hash'] + '/' + datafile, outdir)
                                if status != 200:
                                    log(f"=========> erro {status} ao baixar arquivo de dados, saindo")
                                    return False
                            count_urna+=1
                    count_secao+=1
                count_zona+=1
            count_mu+=1
                            

    return True
    
def main():
    
    baixa_todos = False
    somente_bu = False
    uf = None
    
    try:
        opts,args = getopt.getopt(sys.argv[1:],  "hu:ab", [ "help", "uf=", "all", "bu" ])
    except getopt.GetoptError as err:
        log(err)
        exibe_ajuda()
        exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            exibe_ajuda()
            exit(1)
        elif o in ("-u", "--uf"):
            uf = a
        elif o in ("-a", "--all"):
            baixa_todos = True
        elif o in ("-b", "--bu"):
            somente_bu = True
            
    if uf is None and not baixa_todos:
        log('Necessário informar UF.')
        exit(2)
   
    # obtém a lista de municípios, zonas e seções para um estado
    if baixa_todos:
        for uf in ESTADOS:            
            log(f'Baixando dados de urna para o estado {uf}')
            file = uf + '-p000' + pleito + '-cs.json'
            status, data = baixa_arquivo(base_url + '/arquivo-urna/' + pleito + '/config/' + uf + '/' + file, json_dir)
            if status == 200:
                if processa_estado(os.path.join(json_dir, file), somente_bu):
                    log(f"======> Estado {uf} processado com sucesso.")
                else:
                    log(f"======> Erro ao processar estado {uf}")
                    exit(1)
            else:
                log(f"=========> erro ao baixar dados de urna para o estado {uf}")
                exit(1)
    else:
        log(f'Baixando dados de urna para o estado {uf}')
        file = uf + '-p000' + pleito + '-cs.json'
        status, data = baixa_arquivo(base_url + '/arquivo-urna/' + pleito + '/config/' + uf + '/' + file, json_dir)
        if processa_estado(os.path.join(json_dir, file), somente_bu):
            log(f"======> Estado {uf} processado com sucesso.")
        else:
            log(f"======> Erro ao processar estado {uf}")
            exit(1)
          
    
    return

if __name__ == "__main__":
    main()
    