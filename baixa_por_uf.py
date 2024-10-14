#!/usr/bin/python3

from io import BytesIO
import getopt
import os,sys
import pycurl
import json
import signal
import pdb

from testtools import skip

# dados de url
base_url = 'https://resultados.tse.jus.br/oficial'

# diretório onde salvar os arquivos
json_dir = 'json/'
data_dir = 'data/'

max_download_speed = 0         # 0 = ilimitado, 512*1024 = 512kbit
max_filesize = 300*1024*1024   # Tamanho maximo de arquivo a ser baixado em bytes (300MB)

connect_timeout = 20    # tempo máximo em segundos para efetuar uma conexão
download_timeout = 20   # tempo máximo sem receber dados para cancelar o download
download_retries = 15   # número de tentativas

ESTADOS= [ 'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms', 'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to' ]

# funcao de log
def log(mensagem):
    print(mensagem)
    #syslog.syslog(mensagem)
    return

def exibe_ajuda():
    print('Uso: ')
    print('\t-g|--geral=<identificador geral>\t\tIdentificador geral (ex: ele2022)')
    print('\t-p|--pleito=<id do pleito>\t\t\tIdentificador do Pleito (ex: 406)')
    print('\t-e|--eleicao=<id da eleição>\t\t\tIdentificador da Eleição (ex: 544)')
    print('\t-u|--uf=<estado>\t\t\t\tEstado a consultar')
    print('\t-a|--all\t\t\t\t\tBaixa todos os estados')
    print('\t-b|--bu\t\t\t\t\t\tBaixa apenas os arquivos de BU, ignorando os outros tipos')
    print('\t-i|--imgbu\t\t\t\t\tBaixa apenas os arquivos de espelho de BU, ignorando os outros tipos')
    print('\t-z|--logjez\t\t\t\t\tBaixa apenas os arquivos de log, ignorando os outros tipos')
    print('\t-r|--rdv\t\t\t\t\tBaixa apenas os arquivos de registro de voto, ignorando os outros tipos')
    print('\t-v|--vscmr\t\t\t\t\tBaixa apenas os arquivos de assinaturas, ignorando os outros tipos')
    print('\t-l|--list\t\t\t\t\tLista os identificadores disponíveis na base do TSE')
    print('\t-h|--help\t\t\t\t\tExibe a ajuda')
    return

def signal_handler(sig, frame):
    print('Processo interrompido, fechando...')
    sys.exit(0)
    
# baixa um arquivo
def baixa_arquivo(url, dest_dir, force=False, skipExisting=True):
    status_code = -1
    bytes_size = -1
    fd = None
    filename = os.path.join(dest_dir, os.path.basename(url))
    
    if os.path.exists(filename) and skipExisting:
        log(f"[OK] pulando arquivo {filename} pois já existe e foi solicitado pular")
        return 200, None
    
    if os.path.exists(dest_dir) is False:
        log(f"Diretório {dest_dir} não existe, criando...")
        os.makedirs(dest_dir, mode=0o755)

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
                if (file_size == bytes_size) and skipExisting:
                    log('[OK] arquivo %s já foi baixado completamente (%d bytes).' % (url, bytes_size))
                    return status_code, None
            else:
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

def processa_estado(filename, geral, pleito, eleicao, somente_bu, somente_imgbu, somente_log, somente_rdv, somente_vsmcr):
    
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
                    status, dados_secao = baixa_arquivo(base_url + '/' + geral + '/arquivo-urna/' + pleito + '/dados/' + uf + '/' + mu['cd'] + '/' + zon['cd'] + '/' + sec['ns'] + '/' + file, json_dir)
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
                            
                            if 'nmarq' in urna.keys():
                                datafiles=urna['nmarq'] # nome até as eleições de 2022
                            else:
                                datafiles=urna['arq'] # nome novo nas eleições de 2024-

                            for file in datafiles:
                                datafile = file['nm']
                                # baixa os arquivos relacionados a cada urna
                                # https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.logjez
                                outdir = os.path.join(data_dir, uf, mu['cd'], zon['cd'], sec['ns'])
                                os.makedirs(outdir, exist_ok=True)
                                log(f"\t\t---> baixando log de urna: {datafile} para {outdir}")
                                if somente_bu and not os.path.basename(datafile).endswith(".bu"):
                                    log(f"somente BU será baixado, pulando arquivo {datafile}")
                                    continue
                                if somente_imgbu and not os.path.basename(datafile).endswith(".imgbu"):
                                    log(f"somente espelho de BU será baixado, pulando arquivo {datafile}")
                                    continue
                                if somente_log and not os.path.basename(datafile).endswith(".logjez"):
                                    log(f"somente log será baixado, pulando arquivo {datafile}")
                                    continue
                                if somente_rdv and not os.path.basename(datafile).endswith(".rdv"):
                                    log(f"somente registro de voto será baixado, pulando arquivo {datafile}")
                                    continue
                                if somente_vsmcr and not os.path.basename(datafile).endswith(".vscmr"):
                                    log(f"somente arquivo de assinaturas será baixado, pulando arquivo {datafile}")
                                    continue
                                else:    
                                    status, dados_urna = baixa_arquivo(base_url + '/' + geral + '/arquivo-urna/' + pleito + '/dados/' + uf + '/' + mu['cd'] + '/' + zon['cd'] + '/' + sec['ns'] + '/' + urna['hash'] + '/' + datafile, outdir)
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
    somente_imgbu = False
    somente_log = False
    somente_listar = False
    somente_rdv = False
    somente_vscmr = False
    geral = None
    pleito = None
    eleicao = None
    uf = None
    
    try:
        opts,args = getopt.getopt(sys.argv[1:],  "hg:p:e:u:abizrvl", [ "help", "geral=", "pleito=", "eleicao=", "uf=", "all", "bu", "imgbu", "logjez", "rdv", "vscmr", "list" ])
    except getopt.GetoptError as err:
        log(err)
        exibe_ajuda()
        exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            exibe_ajuda()
            exit(1)
        elif o in ("-g", "--geral"):
            geral = a
        elif o in ("-p", "--pleito"):
            pleito = a
        elif o in ("-e", "--eleicao"):
            eleicao = a
        elif o in ("-u", "--uf"):
            uf = a
        elif o in ("-a", "--all"):
            baixa_todos = True
        elif o in ("-b", "--bu"):
            somente_bu = True
        elif o in ("-i", "--imgbu"):
            somente_imgbu = True
        elif o in ("-z", "--logjez"):
            somente_log = True
        elif o in ("-r", "--rdv"):
            somente_rdv = True
        elif o in ("-v", "--vscmr"):
            somente_vscmr = True            
        elif o in ("-l", "--list"):
            somente_listar = True


    # intercepta o CTRL-C
    signal.signal(signal.SIGINT, signal_handler)

    if somente_listar:
        status, data = baixa_arquivo(base_url + '/comum/config/ele-c.json', json_dir, skipExisting=False, force=True)
        if status == 200:
            with open(os.path.join(json_dir, 'ele-c.json'), 'r') as f:
                dados=json.loads(f.read())
            log(f"\nIDENTIFICADOR GERAL: {dados['c']}")
            log(f"==============================================\n")
            for p in dados['pl']:
                if 'dt' in p.keys():
                    log(f"\n---> PLEITO: {p['cd']} (mandato {p['dt']} a {p['dtlim']})")
                else:
                    log(f"\n---> PLEITO: {p['cd']}")
                for e in p['e']:
                    log(f"Eleição: {e['cd']} - {e['nm']} - (turno: {e['t']})")
                    if 'abr' in e.keys():
                        log(f"-> Detalhes:")
                        for d in e['abr']:
                            # print(d)
                            log(f"\tEstado: {d['cd']}")
                            for c in d['cp']:
                                log(f"\tDescrição: {c['ds']} (código: {c['cd']})")
                            if 'mu' in d.keys():
                                for m in d['mu']:
                                    # print(m)
                                    log(f"\tMunicípio: {m['cd']}")
                            if 'ds' in d.keys():
                                log(f"\t\tDescrição: {d['ds']} (tipo: {d['tp']})")

            exit(0)
        else:
            log(f"Erro ao obter lista.")
            exit(2)
   
    if geral is None or eleicao is None or pleito is None:
        log('Necessário informar identificadores: geral, pleito, eleição. Use "--list" para obter a lista atualizada.')
        exit(2)
            
    if uf is None and not baixa_todos:
        log('Necessário informar UF.')
        exit(2)
   
    # obtém a lista de municípios, zonas e seções para um estado
    if baixa_todos:
        for uf in ESTADOS:            
            log(f'Baixando dados de urna para o estado {uf}')
            file = uf + '-p000' + pleito + '-cs.json'
            status, data = baixa_arquivo(base_url + '/' + geral + '/arquivo-urna/' + pleito + '/config/' + uf + '/' + file, json_dir)
            if status == 200:
                if processa_estado(os.path.join(json_dir, file), geral, pleito, eleicao, somente_bu, somente_imgbu, somente_log, somente_rdv, somente_vscmr):
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
        status, data = baixa_arquivo(base_url + '/' + geral + '/arquivo-urna/' + pleito + '/config/' + uf + '/' + file, json_dir)
        if processa_estado(os.path.join(json_dir, file), geral, pleito, eleicao, somente_bu, somente_imgbu, somente_log, somente_rdv, somente_vscmr):
            log(f"======> Estado {uf} processado com sucesso.")
        else:
            log(f"======> Erro ao processar estado {uf}")
            exit(1)
          
    
    return

if __name__ == "__main__":
    main()
    