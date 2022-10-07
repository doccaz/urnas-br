#!/usr/bin/python3

import getopt
import glob
import json
import pdb
import asn1tools
import sys
import os

asn1_paths = 'doc/spec/bu.asn1'

# funcao de log


def log(mensagem):
    print(mensagem)
    # syslog.syslog(mensagem)
    return


def exibe_ajuda():
    print('Uso: ')
    print('\t-u|--uf=<estado>\t\tEstado a processar')
    print('\t-h|--help\t\tExibe a ajuda')
    return


def processa_bu(asn1_paths: list, bu_path: str):
    conv = asn1tools.compile_files(asn1_paths, codec="ber")
    with open(bu_path, "rb") as file:
        envelope_encoded = bytearray(file.read())

    envelope_decoded = conv.decode(
        "EntidadeEnvelopeGenerico", envelope_encoded)
    bu_encoded = envelope_decoded["conteudo"]
    # remove o conteúdo para não imprimir como array de bytes
    del envelope_decoded["conteudo"]
    bu_decoded = conv.decode("EntidadeBoletimUrna", bu_encoded)

    # municipio, zona, secao, eleitores aptos para votar em presidente, votos para presidente
    return (envelope_decoded['identificacao'][1]['municipioZona']['municipio'], envelope_decoded['identificacao'][1]['municipioZona']['zona'], envelope_decoded['identificacao'][1]['secao'], bu_decoded['resultadosVotacaoPorEleicao'][1]['qtdEleitoresAptos'], bu_decoded['resultadosVotacaoPorEleicao'][1]['resultadosVotacao'][0]['totaisVotosCargo'][0]['votosVotaveis'])


def main():

    uf = None
    secao = None
    resultados = None
    files = []

    if not os.path.exists(asn1_paths):
        log(f"Arquivo {asn1_paths} não encontrado.")
        exit(2)

    try:
        opts, args = getopt.getopt(sys.argv[1:],  "hu:", ["help", "uf="])
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

    if uf is None:
        exibe_ajuda()
        exit(1)

    files = glob.glob('./data/' + uf + '/**/**/**/*.bu')


    log(f"Total de {len(files)} boletins de urna a serem processados")


    # carrega dados de municípios
    with open('./json/' + uf + '-p000406-cs.json', "r") as f:
        dados_estado = json.loads(f.read())
        data = dados_estado['abr'][0]
        log(f"total de {len(data['mu'])} municípios para ({data['ds']} - {data['cd']})")
        
    count=1
    
    with open('resumo-' + uf + '.csv', 'w') as f:
        f.write(f"\"UF\",\"cod_municipio\",\"municipio\",\"zona\",\"secao\",\"eleitores_aptos\",\"candidato\",\"quantidade_votos\"\n")
        for bu in files:
            log(f"[{count}/{len(files)}] processando {bu}")
            try:
                municipio, zona, secao, eleitores_aptos, votos = processa_bu(
                asn1_paths, bu)
            except Exception as e:
                log(f"erro: {e} em {bu}")
                log(f"voto invalido: {voto}")
                exit(1)
            text = ''
            for voto in votos:
                if voto['tipoVoto'] == 'nominal':
                    text = str(voto['identificacaoVotavel']['partido']) + ',' + str(voto['quantidadeVotos']) 
                elif voto['tipoVoto'] == 'nulo':
                    text = 'NULO,' + str(voto['quantidadeVotos'])
                elif voto['tipoVoto'] == 'branco':
                    text = 'BRANCO,' + str(voto['quantidadeVotos'])
                f.write(f"{uf},{municipio},\"{[m for m in data['mu'] if m['cd'] == str(municipio).zfill(5)][0]['nm']}\",{str(zona).zfill(5)},{str(secao).zfill(4)},{eleitores_aptos},{text}\n")
            count+=1
    f.close()
    log(f"UF {uf} concluída com sucesso.")

    return


if __name__ == "__main__":
    main()
