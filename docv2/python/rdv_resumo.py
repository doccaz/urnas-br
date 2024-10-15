"""Imprime o conteúdo do arquivo do RDV"""

import argparse
import logging
import os
import sys
from typing import Tuple

from lib.mr_util import extrai_entidade_decoded


def print_votos_cargo(votos_cargo: list):
    """Imprime os votos de um cargo"""

    print("Digitação | Tipo do voto")
    for voto_cargo in votos_cargo:
        tipo = voto_cargo['tipoVoto']
        digitacao = voto_cargo["digitacao"] if "digitacao" in voto_cargo else "---"
        print(f"{digitacao:9} | {tipo}")


def print_votos_cargos(votos_cargos: list):
    """Imprime os votos dos cargos"""

    for votos_cargo in votos_cargos:
        id_cargo = votos_cargo["idCargo"]
        print("-" * 40)
        print(f"Cargo: {id_cargo[1]}")
        print_votos_cargo(votos_cargo["votos"])


def print_resultados_eleicoes(eleicoes: list):
    """Imprime os resultados das eleições"""

    for eleicao in eleicoes:
        print(f"Id da eleição: {eleicao['idEleicao']}")
        print_votos_cargos(eleicao["votosCargos"])


def processa_rdv(asn1_path: str, rdv_path: str):
    """Processa o RDV"""

    rdv = extrai_entidade_decoded(
        asn1_path, rdv_path, "EntidadeResultadoRDV")[0]["rdv"]
    print(f"Fase: {rdv['fase']}, pleito: {rdv['pleito']}")
    ident = rdv["identificacao"]
    mz = ident["municipioZona"]
    s = ident["secao"]
    print(f"Município: {mz['municipio']}, zona: {mz['zona']}, seção: {s}")
    print_resultados_eleicoes(rdv["eleicoes"][1])


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(
        description="Lê o Registro Digital do Voto (RDV) da Urna e imprime seu resumo",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--asn1", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 do RDV")
    parser.add_argument("-r", "--rdv", type=str, required=True,
                        help="Caminho para o arquivo de RDV originado na UE")
    parser.add_argument("--debug", action="store_true",
                        help="Ativa o modo DEBUG do log")

    args = parser.parse_args()

    rdv_path = args.rdv
    asn1_path = args.asn1
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Imprime o resumo do RDV")
    logging.info(" * arquivo do RDV %s", rdv_path)
    logging.info(" * especificação do arquivo do RDV %s", asn1_path)
    if not os.path.exists(rdv_path):
        logging.error("Arquivo do RDV (%s) não encontrado", rdv_path)
        sys.exit(-1)
    if not os.path.exists(asn1_path):
        logging.error(
            "Arquivo de especificação do RDV (%s) não encontrado", asn1_path)
        sys.exit(-1)

    processa_rdv(asn1_path, rdv_path)

    logging.info("Processamento terminado com sucesso")


if __name__ == "__main__":
    main()
