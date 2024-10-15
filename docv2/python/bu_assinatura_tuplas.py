"""Verifica as tuplas do BU"""

import argparse
import hashlib
import logging
import os
import sys
from typing import Tuple

from ecpy.ecdsa import ECDSA
from ecpy.eddsa import EDDSA
from ecpy.keys import ECPublicKey
from lib.mr_util import extrai_chave_certificado_hw, extrai_entidade_envelopada


def calcula_hash_votacao(res_votacao: dict, hash_tupla: str) -> Tuple[str, int]:
    """Calcula o hash cumulativo da votação"""

    erros = 0
    for totais_votos_cargo in res_votacao["totaisVotosCargo"]:
        # logging.debug("Total votos cargo %s", total_votos_cargo)
        codigo_cargo = totais_votos_cargo["codigoCargo"][1]
        ordem = 0
        for votos_votavel in totais_votos_cargo["votosVotaveis"]:
            ordem += 1
            tipo_voto = votos_votavel["tipoVoto"]
            qtd_votos = votos_votavel["quantidadeVotos"]
            ordem_arq = votos_votavel["ordemGeracaoHash"]
            if "identificacaoVotavel" in votos_votavel:
                identificacao_votavel = votos_votavel["identificacaoVotavel"]
                partido = identificacao_votavel["partido"]
                codigo = identificacao_votavel["codigo"]
                texto = f"{hash_tupla}|{ordem}|{codigo_cargo}|"\
                        f"{tipo_voto}|{qtd_votos}|{codigo}|{partido}"
            else:
                texto = f"{hash_tupla}|{ordem}|{codigo_cargo}|{tipo_voto}|{qtd_votos}"
            hash_tupla = hashlib.sha512(texto.encode(
                "iso8859=1")).digest().hex().upper()
            hash_arq = votos_votavel["hash"].hex().upper()
            if ordem != ordem_arq:
                logging.error("Ordens diferem para %s", texto)
                logging.error(" - ordem no BU:     %d", ordem_arq)
                logging.error(" - ordem calculada: %d", ordem)
                erros += 1
            if hash_tupla != hash_arq:
                logging.error("Hashes diferem para %s", texto)
                logging.error(" - hash no BU:     %s", hash_arq)
                logging.error(" - hash calculado: %s", hash_tupla)
                erros += 1
            logging.debug("Texto votavel:  %s", texto)
            logging.debug("Hash no BU:     %s", hash_arq)
            logging.debug("Hash calculado: %s", hash_tupla)

    return hash_tupla, erros


def calcula_hash_inicial(bu_decoded: dict, resutlado_eleicao: dict) -> str:
    """Calcula o hash inicial do BU ()"""

    id_pleito = bu_decoded["cabecalho"]["idEleitoral"][1]
    id_eleicao = resutlado_eleicao["idEleicao"]
    mzs = bu_decoded["urna"]["correspondenciaResultado"]["identificacao"][1]
    mun = mzs["municipioZona"]["municipio"]
    zon = mzs["municipioZona"]["zona"]
    sec = mzs["secao"]
    cod_carga = bu_decoded["urna"]["correspondenciaResultado"]["carga"]["codigoCarga"]
    texto = f"{id_pleito:05}|{id_eleicao:05}|{mun:05}|{zon:04}|{sec:04}|{cod_carga:24}"
    logging.debug("Texto inicial %s", texto)
    texto = texto.encode("iso8859=1")

    hashed = hashlib.sha512(texto).digest()
    return hashed.hex().upper()


def processa_bu(asn1_path: str, bu_path: str, chave: ECPublicKey, verificador: (ECDSA | EDDSA)) -> int:
    """Processa a validação da assinatura das tuplas do BU"""

    erros = 0
    bu_decoded, _ = extrai_entidade_envelopada(
        asn1_path, bu_path, "EntidadeBoletimUrna")
    for res_por_eleicao in bu_decoded["resultadosVotacaoPorEleicao"]:
        eleicao = f"Eleição {res_por_eleicao['idEleicao']}"
        hash_tupla = calcula_hash_inicial(bu_decoded, res_por_eleicao)
        logging.debug("%s - hash inicial %s", eleicao, hash_tupla)
        for res_votacao in res_por_eleicao["resultadosVotacao"]:
            hash_tupla, err = calcula_hash_votacao(res_votacao, hash_tupla)
            erros += err
        hash_arq = res_por_eleicao["ultimoHashVotosVotavel"].hex().upper()
        if hash_tupla != hash_arq:
            logging.error("%s - Hashes finais diferem", eleicao)
            logging.error(" - hash no BU:     %s", hash_arq)
            logging.error(" - hash calculado: %s", hash_tupla)
            erros += 1
        logging.debug("%s - hash final no BU:     %s", eleicao, hash_arq)
        logging.debug("%s - hash final calculado: %s", eleicao, hash_tupla)
        assinatura = res_por_eleicao["assinaturaUltimoHashVotosVotavel"]
        logging.debug("%s - assinatura do hash final: %s",
                      eleicao, assinatura.hex().upper())
        msg = bytes.fromhex(hash_tupla)
        msg = hashlib.sha512(msg).digest()
        if not verificador.verify(msg, assinatura, chave):
            logging.error("%s - Assinatura inválida de %s",
                          eleicao, hash_tupla)
            erros += 1

    return erros


def main():
    """Valida os hashes das tuplas do BU e lê a chave de validação e as assinaturas"""

    parser = argparse.ArgumentParser(
        description="Valida os hashes das tuplas do BU e lê a chave de validação e as assinaturas",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--asn1-bu", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 do BU")
    parser.add_argument("-b", "--bu", type=str, required=True,
                        help="Caminho para o arquivo de BU originado na UE")
    parser.add_argument("-t", "--asn1-assinatura", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 das assinaturas")
    parser.add_argument("-s", "--assinatura", type=str, required=True,
                        help="Caminho para o arquivo de assinatura")
    parser.add_argument("--debug", action="store_true",
                        help="ativa o modo DEBUG do log")

    args = parser.parse_args()

    bu_path = args.bu
    asn1_bu_path = args.asn1_bu
    asn1_vsc_path = args.asn1_assinatura
    vsc_path = args.assinatura

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info(
        "Validação dos hashes das tuplas e da assinatura do hash final do BU")
    logging.info("* arquivo do BU %s", bu_path)
    logging.info("* especificação do BU %s", asn1_bu_path)
    logging.info("* arquivo de assinaturas %s", vsc_path)
    logging.info("* especificação do arquivo de assinaturas %s", asn1_vsc_path)
    if not os.path.exists(bu_path):
        logging.error("Arquivo do BU (%s) não encontrado", bu_path)
        sys.exit(-1)
    if not os.path.exists(asn1_bu_path):
        logging.error(
            "Arquivo de especificação do BU (%s) não encontrado", asn1_bu_path)
        sys.exit(-1)
    if not os.path.exists(vsc_path):
        logging.error(
            "Arquivo de assinaturas (%s) não encontrado", vsc_path)
        sys.exit(-1)
    if not os.path.exists(asn1_vsc_path):
        logging.error(
            "Arquivo de especificação de assinaturas (%s) não encontrado", asn1_vsc_path)
        sys.exit(-1)

    _, _, chave, verificador = extrai_chave_certificado_hw(
        asn1_vsc_path, vsc_path)

    erros = processa_bu(asn1_bu_path, bu_path, chave, verificador)

    if erros == 0:
        logging.info("Validação terminada com sucesso")
        sys.exit(0)
    else:
        logging.error("Validação terminada com erros")
        sys.exit(-1)


if __name__ == "__main__":
    main()
