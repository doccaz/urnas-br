"""Verifica os hashes dos arquivos de resultado da Urna"""

import argparse
import hashlib
import logging
import os
import sys
from typing import Tuple

from asn1tools import compile_files
from asn1tools.compiler import Specification
from ecpy.ecdsa import ECDSA
from ecpy.eddsa import EDDSA
from ecpy.keys import ECPublicKey
from lib.mr_util import (extrai_chave_certificado_hw, extrai_entidade_decoded,
                         valida_certificado)


def verifica_hash(origem: str, resumo: bytes, conteudo: bytes) -> str:
    """Verifica se o hash do conteúdo é igual ao hash esperado"""

    sha = hashlib.sha512()
    sha.update(conteudo)
    digest = sha.digest()

    if digest != resumo:
        return (False, f"{origem}: {digest.hex()}\nda assinatura: {resumo.hex()}")
    else:
        return (True, "OK")


def verifica_hash_arquivo(path: str, resumo: bytes) -> str:
    """Lê o conteúdo do arquivo e verifica se o hash é o esperado"""

    with open(path, "rb") as file:
        conteudo = file.read()

    return verifica_hash("do arquivo", resumo, conteudo)


def verifica_hashes_arquivos(dir_arqs: str, assinaturas: dict):
    """Verifica os hashes dos arquivos de listados em `assinaturas`"""

    erros = 0
    for assinatura_arquivo in assinaturas["arquivosAssinados"]:
        nome_arquivo = assinatura_arquivo["nomeArquivo"]
        path = os.path.join(dir_arqs, nome_arquivo)
        logging.info("Validando hash do arquivo %s", nome_arquivo)

        if not os.path.isfile(path):
            logging.error("Arquivo não encontrado %s", nome_arquivo)
            erros += 1
            continue

        resumo = assinatura_arquivo["assinatura"]["hash"]
        res = verifica_hash_arquivo(path, resumo)
        if not res[0]:
            logging.error("Hash do arquivo %s está incorreto", nome_arquivo)
            print(f"{res[1]}")
            erros += 1

    return erros


def verifica_hashes_de(path: str, ent_assinatura: dict, campo: str, conv: Specification):
    """Verifica os hashes dos listados no campo `campo` do envelope"""

    entidade_assinatura = ent_assinatura[campo]
    assinaturas_encoded = entidade_assinatura["conteudoAutoAssinado"]

    erros = 0
    auto_hash = entidade_assinatura["autoAssinado"]["assinatura"]["hash"]
    res = verifica_hash("do conteúdo", auto_hash, assinaturas_encoded)
    if not res[0]:
        logging.error(
            "Validando %s - hash do conteúdo do aruqivo de assinatura está incorreto", campo)
        print(f"{res[1]}")
        erros += 1

    assinaturas_decoded = conv.decode("Assinatura", assinaturas_encoded)
    erros += verifica_hashes_arquivos(path, assinaturas_decoded)
    return erros


def verifica_hashes(dir_arquivos: str, ent_assinatura: dict, conv: Specification) -> int:
    """Verifica os hashes dos arquivos de listados no arquivo `assinatura_path`"""
    erros = 0
    erros += verifica_hashes_de(dir_arquivos,
                                ent_assinatura, "assinaturaSW", conv)
    erros += verifica_hashes_de(dir_arquivos,
                                ent_assinatura, "assinaturaHW", conv)
    return erros


def valida_assinturas(dir_arquivos: str, conv: Specification, ent_assinatura: dict,
                      x509: dict, chave: ECPublicKey, verificador: (ECDSA | EDDSA)) -> int:
    """Valida as assinaturas dos arquivos"""
    erros = 0

    logging.info("Validando assinatura do certificado")
    if not valida_certificado(x509, verificador):
        logging.error("Certificado inválido")
        erros += 1

    conteudo_auto_ass = conv.decode(
        'Assinatura', ent_assinatura["assinaturaHW"]["conteudoAutoAssinado"])
    arquivos_assinados = conteudo_auto_ass["arquivosAssinados"]
    for arquivo in arquivos_assinados:
        nome_arquivo = arquivo["nomeArquivo"]
        hash_arquivo = arquivo["assinatura"]["hash"]
        ass_arquivo = arquivo["assinatura"]["assinatura"]
        logging.info("Validando assinatura do arquivo: %s", nome_arquivo)
        logging.debug("Hash do arquivo: %s", hash_arquivo.hex().upper())
        logging.debug("Assinatura do arquivo: %s", ass_arquivo.hex().upper())

        path_arquivo = os.path.join(dir_arquivos, nome_arquivo)
        if not os.path.exists(path_arquivo):
            logging.error("Arquivo não encontrado %s", path_arquivo)
            erros += 1
            continue

        if not verificador.verify(hashlib.sha512(hash_arquivo).digest(), ass_arquivo, chave):
            logging.error("Assinatura inválida %s", path_arquivo)
            erros += 1
            continue

    return erros


def le_arq_assinaturas(asn1_path: str, assinatura_path: str) -> Tuple[Specification, dict]:
    """Carrega o arquivo de assinaturas da urna para as validações"""

    conv = compile_files([asn1_path], codec="ber", numeric_enums=True)
    with open(assinatura_path, "rb") as file:
        envelope_encoded = bytearray(file.read())
    envelope_decoded = conv.decode(
        "EntidadeAssinaturaEcourna", envelope_encoded)
    return conv, envelope_decoded


def main():
    """Ponto de entrada do programa"""

    parser = argparse.ArgumentParser(description="Valida o arquivo de assinaturas Urna",
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

    logging.info("Valida as assinaturas dos arquivos de resultado")
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

    dir_arquivos = os.path.dirname(assinatura_path)

    ent_assinatura, conv = extrai_entidade_decoded(
        asn1_path, assinatura_path, "EntidadeAssinaturaEcourna")

    erros = verifica_hashes(dir_arquivos, ent_assinatura, conv)

    x509, _, chave, verificador = extrai_chave_certificado_hw(
        asn1_path, assinatura_path)

    erros += valida_assinturas(dir_arquivos, conv,
                               ent_assinatura, x509, chave, verificador)

    if erros == 0:
        logging.info("Validação terminada com sucesso")
        sys.exit(0)
    else:
        logging.error("Validação terminada com erros")
        sys.exit(-1)


if __name__ == "__main__":
    main()
