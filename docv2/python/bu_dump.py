"""Imprime o conteúdo do arquivo do BU"""

import argparse
import logging
import os
import sys

from lib.mr_util import extrai_entidade_decoded, print_dict, print_membro


def processa_bu(asn1_path: str, bu_path: str):
    """Processa o BU"""

    envelope, conv = extrai_entidade_decoded(
        asn1_path, bu_path, "EntidadeEnvelopeGenerico")

    bu_encoded = envelope["conteudo"]
    # remove o conteúdo para não imprimir como array de bytes
    del envelope["conteudo"]
    print("EntidadeEnvelopeGenerico:")
    print_dict(envelope, 1)
    bu_decoded = conv.decode("EntidadeBoletimUrna", bu_encoded)
    print_membro(bu_decoded, "EntidadeBoletimUrna", 0)


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(
        description="Lê um Boletim de Urna (BU) da Urna e imprime seu conteúdo",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--asn1", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 do BU")
    parser.add_argument("-b", "--bu", type=str, required=True,
                        help="Caminho para o arquivo de BU originado na UE")
    parser.add_argument("--debug", action="store_true",
                        help="ativa o modo DEBUG do log")

    args = parser.parse_args()

    bu_path = args.bu
    asn1_path = args.asn1
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Imprime o conteúdo do BU")
    logging.info(" * arquivos do BU %s", bu_path)
    logging.info(" * especificação do arquivo do BU %s", asn1_path)
    if not os.path.exists(bu_path):
        logging.error("Arquivo do BU (%s) não encontrado", bu_path)
        sys.exit(-1)
    if not os.path.exists(asn1_path):
        logging.error(
            "Arquivo de especificação do BU (%s) não encontrado", asn1_path)
        sys.exit(-1)

    processa_bu(asn1_path, bu_path)

    logging.info("Processamento terminado com sucesso")


if __name__ == "__main__":
    main()
