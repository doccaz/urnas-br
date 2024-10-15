"""Extrai o certificado do arquivo de assinaturas da urna e salva em um arquivo"""

import argparse
import logging
import os
import sys

from lib.mr_util import ModeloHW, extrai_certificado_hw


def extrai_certificado(asn1_path: str, assinatura_path: str, nome_certificado: str):
    """Extrai o certificado do arquivo de assinatura"""

    certificado, modelo = extrai_certificado_hw(asn1_path, assinatura_path)

    extensao = ".pem" if modelo in (
        ModeloHW.UE2020, ModeloHW.UE2022) else ".der"
    nome = nome_certificado + extensao
    logging.info("Criando certificado %s", nome)
    with open(nome, "wb") as file:
        file.write(certificado)


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(
        description="Le o arquivo de assinaturas da Urna Eletrônica (UE) e extrai o certificado",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--asn1", type=str, required=True,
                        help="Caminho para o arquivo de especificação asn1 das assinaturas")
    parser.add_argument("-s", "--assinatura", type=str, required=True,
                        help="Caminho para o arquivo de assinatura originado na UE")
    parser.add_argument("-o", "--output", type=str, required=True,
                        help="Caminho para o arquivo de certificado (sem extensão)")
    parser.add_argument("--debug", action="store_true",
                        help="ativa o modo DEBUG do log")

    args = parser.parse_args()

    assinatura_path = args.assinatura
    asn1_path = args.asn1
    nome_certificado = args.output
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Extrai o certificado do arquivo de assinaturas")
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

    extrai_certificado(asn1_path, assinatura_path, nome_certificado)

    logging.info("Processamento terminado com sucesso")


if __name__ == "__main__":
    main()
