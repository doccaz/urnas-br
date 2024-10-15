"""Imprime o conteúdo do arquivo de assinaturas"""

import argparse
import copy
import logging
import os
import sys

from lib.mr_util import extrai_entidade_decoded, print_membro


def print_entidade_assinatura(entidade_assinatura: dict, name: str, profundidade: int, conv):
    """Imprime o conteúdo de um membro que é EntidadeAssinatura"""

    # copiado para evitar que seja impresso como binário
    conteudo = copy.copy(entidade_assinatura["conteudoAutoAssinado"])
    # deleta o campo porque ele será impresso decodificado
    del entidade_assinatura["conteudoAutoAssinado"]
    print_membro(entidade_assinatura, name, profundidade)
    assinatura = conv.decode("Assinatura", conteudo)
    print_membro(assinatura, "conteudoAutoAssinado", profundidade + 1)


def processa_assinaturas(asn1_path: str, assinatura_path: str):
    """Imprime o conteúdo de um membro que é EntidadeAssinaturaEcourna"""

    envelope, conv = extrai_entidade_decoded(
        asn1_path, assinatura_path, "EntidadeAssinaturaEcourna")

    assinatura_sw = copy.copy(envelope["assinaturaSW"])
    assinatura_hw = copy.copy(envelope["assinaturaHW"])
    # remove o conteúdo para não imprimir como array de bytes
    del envelope["assinaturaSW"]
    del envelope["assinaturaHW"]

    print_membro(envelope, "EntidadeAssinaturaEcourna", 0)
    print_entidade_assinatura(assinatura_sw, "Assinatura SW", 1, conv)
    print_entidade_assinatura(assinatura_hw, "Assinatura HW", 1, conv)


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(
        description="Lê o arquivo de assinaturas da Urna e imprime seu conteúdo",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--asn1", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 das assinaturas")
    parser.add_argument("-s", "--assinatura", type=str, required=True,
                        help="Caminho para o arquivo de assinatura originado na UE")
    parser.add_argument("--debug", action="store_true",
                        help="ativa o modo DEBUG do log")

    args = parser.parse_args()

    assinatura_path = args.assinatura
    asn1_path = args.asn1
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Imprime o conteúdo do arquivo de assinaturas")
    logging.info(" * arquivo de assinaturas %s", assinatura_path)
    logging.info(" * especificação do arquivo de assinaturas %s", asn1_path)
    if not os.path.exists(assinatura_path):
        logging.error(
            "Arquivo de assinaturas (%s) não encontrado", assinatura_path)
        sys.exit(-1)
    if not os.path.exists(asn1_path):
        logging.error(
            "Arquivo de especificação das assinaturas (%s) não encontrado", asn1_path)
        sys.exit(-1)

    processa_assinaturas(asn1_path, assinatura_path)

    logging.info("Processamento terminado com sucesso")


if __name__ == "__main__":
    main()
