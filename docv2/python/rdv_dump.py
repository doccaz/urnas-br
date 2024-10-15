"""Imprime o conteúdo do arquivo do RDV"""

import argparse
import logging
import os
import sys

from lib.mr_util import extrai_entidade_decoded, print_membro


def processa_rdv(asn1_path: str, rdv_path: str):
    """Processa o RDV"""

    rdv, _ = extrai_entidade_decoded(
        asn1_path, rdv_path, "EntidadeResultadoRDV")
    print_membro(rdv, "EntidadeResultadoRDV", 0)


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(
        description="Lê o Registro Digital do Voto (RDV) da Urna e imprime seu conteúdo",
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

    logging.info("Imprime o conteúdo do RDV")
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
