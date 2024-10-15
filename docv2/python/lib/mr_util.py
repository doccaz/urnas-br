"""Utilitários de certificados."""

import hashlib
import logging
from base64 import b64decode
from enum import Enum
from typing import Any, Dict, Tuple

import asn1tools
from asn1tools.compiler import Specification
from ecpy.curves import Curve
from ecpy.ecdsa import ECDSA
from ecpy.eddsa import EDDSA
from ecpy.keys import ECPublicKey
from OpenSSL import crypto

# dump de entidades - BEGIN ####################################################################


def _indenta(profundidade: int):
    """Indenta o texto"""

    return ".   " * profundidade


def _valor_membro(membro):
    """Converte o conteúdo para texto hexa se for bytes"""

    if isinstance(membro, (bytes, bytearray)):
        return bytes(membro).hex()
    return membro


def print_list(lista: list | tuple, profundidade: int, key: str):
    """Imprime uma lista de valores"""

    abertura, fechamento = ("[", "]") if isinstance(
        lista, list) else ("(", ")")
    indent = _indenta(profundidade)
    print(f"{indent}{abertura}")
    for membro in lista:
        if isinstance(membro, dict):
            print_dict(membro, profundidade + 1)
        else:
            print_conteudo_membro(membro, profundidade + 1)

    if not key:
        key = "sem nome"
    print(f"{indent}{fechamento} <== {key}")


def print_dict(entidade: dict, profundidade: int):
    """Imprime um dicionário de valores"""

    indent = _indenta(profundidade)
    print(f"{indent}{{")
    for key in sorted(entidade):
        membro = entidade[key]
        print_membro(membro, key, profundidade + 1)
    print(f"{indent}}}")


def print_conteudo_membro(membro, profundidade: int):
    """Imprime o conteúdo de um membro (recursivamente)"""

    indent = _indenta(profundidade)
    if isinstance(membro, dict):
        print_dict(membro, profundidade)
    elif isinstance(membro, (list, tuple)):
        print_list(membro, profundidade, "")
    else:
        print(f"{indent}{_valor_membro(membro)}")


def print_membro(membro, key: str, profundidade: int):
    """Imprime um membro (recursivamente)"""

    indent = _indenta(profundidade)
    if isinstance(membro, dict):
        print(f"{indent}{key}:")
        print_dict(membro, profundidade)
    elif isinstance(membro, (list, tuple)):
        print(f"{indent}{key}:")
        print_list(membro, profundidade, key)
    else:
        print(f"{indent}{key} = {_valor_membro(membro)}")


# dump de entidades - END ######################################################################


def extrai_entidade_decoded(asn1_path: str,
                            data_path: str,
                            nome_entidade: str) -> Tuple[dict, Specification]:
    """Extrai do arquivo `data_path` a entidade de nome `nome_entidade` especificada em `asn1_path`
    """

    conv = asn1tools.compile_files(
        [asn1_path], codec="ber", numeric_enums=True)
    with open(data_path, "rb") as bu:
        encoded = bytearray(bu.read())
    decoded = conv.decode(nome_entidade, encoded)

    return decoded, conv


def extrai_entidade_envelopada(asn1_path: str,
                               data_path: str,
                               nome_entidade: str) -> Tuple[dict, Specification]:
    """Extrai do arquivo `data_path` a entidade de nome `nome_entidade` envelopada em
        `EntidadeEnvelopeGenerico` no campo `conteudo`, especificadas em `asn1_path`
    """

    envelope, conv = extrai_entidade_decoded(
        asn1_path, data_path, "EntidadeEnvelopeGenerico")

    encoded = envelope["conteudo"]
    decoded = conv.decode(nome_entidade, encoded)

    return decoded, conv


def decode_x509(certificado: bytes) -> dict:
    """Decodifica um certificado X.509"""
    return _X509_DECODER.decode("Certificate", certificado)


class ModeloHW(Enum):
    """Modelo de HW"""
    TPM12 = 1
    TPM20 = 2
    UE2009 = 9
    UE2010 = 10
    UE2011 = 11
    UE2013 = 13
    UE2015 = 15
    UE2020 = 20
    UE2022 = 22

    def __str__(self) -> str:
        if self.value == 1:
            res = "TPM 1.2"
        if self.value == 2:
            res = "TPM 2.0"
        if self.value == 9:
            res = "UE 2009"
        if self.value == 10:
            res = "UE 2010"
        if self.value == 11:
            res = "UE 2011"
        if self.value == 13:
            res = "UE 2013"
        if self.value == 15:
            res = "UE 2015"
        if self.value == 20:
            res = "UE 2020"
        if self.value == 22:
            res = "UE 2022"
        return res


def _modelo(modelo: int) -> ModeloHW:
    """Retorna o modelo de hardware correspondente ao ID"""
    if modelo == 1:
        res = ModeloHW.TPM12
    elif modelo == 2:
        res = ModeloHW.TPM20
    elif modelo == 9:
        res = ModeloHW.UE2009
    elif modelo == 10:
        res = ModeloHW.UE2010
    elif modelo == 11:
        res = ModeloHW.UE2011
    elif modelo == 13:
        res = ModeloHW.UE2013
    elif modelo == 15:
        res = ModeloHW.UE2015
    elif modelo == 20:
        res = ModeloHW.UE2020
    elif modelo == 22:
        res = ModeloHW.UE2022
    else:
        raise ValueError(f"Modelo de hardware desconhecido: {modelo}")

    return res


def converte_certificado_para_x509(certificado: bytes, modelo: ModeloHW) -> bytes:
    """Lê o certificado do arquivo de assinaturas da urna"""

    if modelo in (ModeloHW.UE2020, ModeloHW.UE2022):
        logging.debug("Certificado\n %s", certificado.decode("utf-8"))
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, certificado)
    else:
        logging.debug("Certificado %s", certificado.hex().upper())
        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, certificado)
    issuer = cert.get_issuer()
    logging.debug("Emissor do certificado %s / %s / %s",
                  issuer.organizationName, issuer.commonName, issuer.emailAddress)
    return crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)


def extrai_certificado_hw(asn1_path: str, vsc_path: str) -> Tuple[bytes, ModeloHW]:
    """Extrai o certificado do arquivo de assinaturas da urna"""

    ent_assinatura, _ = extrai_entidade_decoded(
        asn1_path, vsc_path, "EntidadeAssinaturaEcourna")

    modelo = _modelo(ent_assinatura["modeloEquipamento"])
    logging.debug("Modelo do HW: %s", modelo)

    assinatura_hw = ent_assinatura["assinaturaHW"]
    certificado = assinatura_hw["certificadoDigital"]
    return certificado, modelo


def extrai_chave_do_certificado(x509: dict) -> Tuple[dict, bytes, ECPublicKey, (ECDSA | EDDSA)]:
    """Lê a chave de validação das assinaturas das tuplas e retorna
        o certificado decodificado
        os bytes da chave
        a chave (objeto)
        e o verificador
    """

    key_info = x509["tbsCertificate"]["subjectPublicKeyInfo"]
    algo = key_info["algorithm"]["algorithm"]
    bytes_chave = key_info["subjectPublicKey"][0]
    if algo == "1.2.840.10045.2.1":
        verificador = ECDSA()
        curve = Curve.get_curve('secp521r1')
    elif algo == "1.3.6.1.4.1.44588.2.1":
        verificador = EDDSA(hashlib.shake_256, hash_len=132)
        curve = Curve.get_curve('Ed521')
    else:
        raise RuntimeError(f"Algoritmo da certificado não reconhecido: {algo}")

    chave = ECPublicKey(curve.decode_point(bytes_chave))

    return x509, bytes_chave, chave, verificador


def extrai_chave_certificado_hw(asn1_path: str, vsc_path: str) -> Tuple[dict, bytes, ECPublicKey, Any]:
    """Lê a chave de validação das assinaturas das tuplas e retorna
        o certificado decodificado
        os bytes da chave
        a chave (objeto)
        e o validador
    """

    certificado, modelo = extrai_certificado_hw(asn1_path, vsc_path)
    cert_vsc = converte_certificado_para_x509(certificado, modelo)
    x509 = decode_x509(cert_vsc)
    return extrai_chave_do_certificado(x509)


def common_name(nomes: dict) -> str:
    """Recupera o nome comum do conjunto de nomes (subject ou issuer)"""

    for nome in nomes:
        for dict_nome in nome:
            if dict_nome["type"] == _OID_COMMON_NAME:
                value = dict_nome["value"]
                assert value[0] in (0x13, 0xC), f"Valor inválido {value[0]}"
                return value[2:2 + value[1]].decode("utf-8")
    raise ValueError(f"Nome comum não encontrado ({_OID_COMMON_NAME})")


def carrega_chaves_pems(pems: list[str]) -> Dict[str, ECPublicKey]:
    """Carrega as chaves PEMs"""

    chaves = {}
    for pem in pems:
        certificado = decode_x509(b64decode(pem))
        _, _, chave, _ = extrai_chave_do_certificado(certificado)
        nome = common_name(certificado["tbsCertificate"]["subject"][1])
        chaves[nome] = chave
    return chaves


def chave_do_emissor(emissor: str) -> ECPublicKey:
    """Carrega a chave do emissor"""

    if emissor not in _CHAVES_RAIZ:
        raise ValueError(f"Chave do emissor {emissor} não encontrada")

    return _CHAVES_RAIZ[emissor]


def valida_certificado(x509: dict, verificador) -> bool:
    """Valida o certificado com um dos certificados raiz"""
    nome_emissor = common_name(x509["tbsCertificate"]["issuer"][1])
    chave_emissor = chave_do_emissor(nome_emissor)
    msg = _X509_DECODER.encode("TBSCertificate", x509["tbsCertificate"])
    if isinstance(verificador, ECDSA):
        msg = hashlib.sha512(msg).digest()
    return verificador.verify(msg, x509["signature"][0], chave_emissor)


_OID_COMMON_NAME = "2.5.4.3"  # http://oid-info.com/get/2.5.4.3


# Obtido de https://www.rfc-editor.org/rfc/rfc5280#appendix-A
_X509_ASN1 = """
PKIX1Explicit88 { iso(1) identified-organization(3) dod(6) internet(1)
                security(5) mechanisms(5) pkix(7) id-mod(0) id-pkix1-explicit(18) }

DEFINITIONS EXPLICIT TAGS ::=

BEGIN

-- PKIX specific OIDs

id-pkix OBJECT IDENTIFIER ::=
        { iso(1) identified-organization(3) dod(6) internet(1)
                    security(5) mechanisms(5) pkix(7) }

-- PKIX arcs

id-pe OBJECT IDENTIFIER ::= { id-pkix 1 }
        -- arc for private certificate extensions
id-qt OBJECT IDENTIFIER ::= { id-pkix 2 }
        -- arc for policy qualifier types
id-kp OBJECT IDENTIFIER ::= { id-pkix 3 }
        -- arc for extended key purpose OIDS
id-ad OBJECT IDENTIFIER ::= { id-pkix 48 }
        -- arc for access descriptors

-- policyQualifierIds for Internet policy qualifiers

id-qt-cps       OBJECT IDENTIFIER ::=  { id-qt 1 }
    -- OID for CPS qualifier
id-qt-unotice   OBJECT IDENTIFIER ::=  { id-qt 2 }
    -- OID for user notice qualifier

-- access descriptor definitions

id-ad-ocsp          OBJECT IDENTIFIER ::= { id-ad 1 }
id-ad-caIssuers     OBJECT IDENTIFIER ::= { id-ad 2 }
id-ad-timeStamping  OBJECT IDENTIFIER ::= { id-ad 3 }
id-ad-caRepository  OBJECT IDENTIFIER ::= { id-ad 5 }

-- attribute data types

Attribute ::= SEQUENCE {
    type    AttributeType,
    values  SET OF AttributeValue
    -- at least one value is required
}

AttributeType ::= OBJECT IDENTIFIER

AttributeValue ::= ANY -- DEFINED BY AttributeType

AttributeTypeAndValue ::= SEQUENCE {
    type    AttributeType,
    value   AttributeValue
}

-- suggested naming attributes: Definition of the following
--   information object set may be augmented to meet local
--   requirements.  Note that deleting members of the set may
--   prevent interoperability with conforming implementations.
-- presented in pairs: the AttributeType followed by the
--   type definition for the corresponding AttributeValue

-- Arc for standard naming attributes

id-at OBJECT IDENTIFIER ::= { joint-iso-ccitt(2) ds(5) 4 }

-- Naming attributes of type X520name

id-at-name                  AttributeType ::= { id-at 41 }
id-at-surname               AttributeType ::= { id-at  4 }
id-at-givenName             AttributeType ::= { id-at 42 }
id-at-initials              AttributeType ::= { id-at 43 }
id-at-generationQualifier   AttributeType ::= { id-at 44 }

-- Naming attributes of type X520Name:
--   X520name ::= DirectoryString (SIZE (1..ub-name))
--
-- Expanded to avoid parameterized type:
X520name ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-name)),
    printableString PrintableString (SIZE (1..ub-name)),
    universalString UniversalString (SIZE (1..ub-name)),
    utf8String      UTF8String      (SIZE (1..ub-name)),
    bmpString       BMPString       (SIZE (1..ub-name))
}

-- Naming attributes of type X520CommonName

id-at-commonName AttributeType ::= { id-at 3 }

-- Naming attributes of type X520CommonName:
--   X520CommonName ::= DirectoryName (SIZE (1..ub-common-name))
--
-- Expanded to avoid parameterized type:
X520CommonName ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-common-name)),
    printableString PrintableString (SIZE (1..ub-common-name)),
    universalString UniversalString (SIZE (1..ub-common-name)),
    utf8String      UTF8String      (SIZE (1..ub-common-name)),
    bmpString       BMPString       (SIZE (1..ub-common-name))
}

-- Naming attributes of type X520LocalityName

id-at-localityName AttributeType ::= { id-at 7 }

-- Naming attributes of type X520LocalityName:
--   X520LocalityName ::= DirectoryName (SIZE (1..ub-locality-name))
--
-- Expanded to avoid parameterized type:
X520LocalityName ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-locality-name)),
    printableString PrintableString (SIZE (1..ub-locality-name)),
    universalString UniversalString (SIZE (1..ub-locality-name)),
    utf8String      UTF8String      (SIZE (1..ub-locality-name)),
    bmpString       BMPString       (SIZE (1..ub-locality-name))
}

-- Naming attributes of type X520StateOrProvinceName

id-at-stateOrProvinceName AttributeType ::= { id-at 8 }

-- Naming attributes of type X520StateOrProvinceName:
--   X520StateOrProvinceName ::= DirectoryName (SIZE (1..ub-state-name))
--
-- Expanded to avoid parameterized type:
X520StateOrProvinceName ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-state-name)),
    printableString PrintableString (SIZE (1..ub-state-name)),
    universalString UniversalString (SIZE (1..ub-state-name)),
    utf8String      UTF8String      (SIZE (1..ub-state-name)),
    bmpString       BMPString       (SIZE (1..ub-state-name))
}

-- Naming attributes of type X520OrganizationName

id-at-organizationName AttributeType ::= { id-at 10 }

-- Naming attributes of type X520OrganizationName:
--   X520OrganizationName ::=
--          DirectoryName (SIZE (1..ub-organization-name))
--
-- Expanded to avoid parameterized type:
X520OrganizationName ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-organization-name)),
    printableString PrintableString (SIZE (1..ub-organization-name)),
    universalString UniversalString (SIZE (1..ub-organization-name)),
    utf8String      UTF8String      (SIZE (1..ub-organization-name)),
    bmpString       BMPString       (SIZE (1..ub-organization-name))
}

-- Naming attributes of type X520OrganizationalUnitName

id-at-organizationalUnitName AttributeType ::= { id-at 11 }

-- Naming attributes of type X520OrganizationalUnitName:
--   X520OrganizationalUnitName ::=
--          DirectoryName (SIZE (1..ub-organizational-unit-name))
--
-- Expanded to avoid parameterized type:
X520OrganizationalUnitName ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-organizational-unit-name)),
    printableString PrintableString (SIZE (1..ub-organizational-unit-name)),
    universalString UniversalString (SIZE (1..ub-organizational-unit-name)),
    utf8String      UTF8String      (SIZE (1..ub-organizational-unit-name)),
    bmpString       BMPString       (SIZE (1..ub-organizational-unit-name))
}

-- Naming attributes of type X520Title

id-at-title AttributeType ::= { id-at 12 }

-- Naming attributes of type X520Title:
--   X520Title ::= DirectoryName (SIZE (1..ub-title))
--
-- Expanded to avoid parameterized type:
X520Title ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..ub-title)),
    printableString PrintableString (SIZE (1..ub-title)),
    universalString UniversalString (SIZE (1..ub-title)),
    utf8String      UTF8String      (SIZE (1..ub-title)),
    bmpString       BMPString       (SIZE (1..ub-title))
}

-- Naming attributes of type X520dnQualifier

id-at-dnQualifier       AttributeType ::= { id-at 46 }

X520dnQualifier ::=     PrintableString

-- Naming attributes of type X520countryName (digraph from IS 3166)

id-at-countryName       AttributeType ::= { id-at 6 }

X520countryName ::=     PrintableString (SIZE (2))

-- Naming attributes of type X520SerialNumber

id-at-serialNumber      AttributeType ::= { id-at 5 }

X520SerialNumber ::=    PrintableString (SIZE (1..ub-serial-number))

-- Naming attributes of type X520Pseudonym

id-at-pseudonym         AttributeType ::= { id-at 65 }

-- Naming attributes of type X520Pseudonym:
--   X520Pseudonym ::= DirectoryName (SIZE (1..ub-pseudonym))
--
-- Expanded to avoid parameterized type:
X520Pseudonym ::= CHOICE {
    teletexString    TeletexString   (SIZE (1..ub-pseudonym)),
    printableString  PrintableString (SIZE (1..ub-pseudonym)),
    universalString  UniversalString (SIZE (1..ub-pseudonym)),
    utf8String       UTF8String      (SIZE (1..ub-pseudonym)),
    bmpString        BMPString       (SIZE (1..ub-pseudonym))
}

-- Naming attributes of type DomainComponent (from RFC 4519)

id-domainComponent  AttributeType ::= { 0 9 2342 19200300 100 1 25 }

DomainComponent ::= IA5String

-- Legacy attributes

pkcs-9 OBJECT IDENTIFIER ::=
       { iso(1) member-body(2) us(840) rsadsi(113549) pkcs(1) 9 }

id-emailAddress     AttributeType ::= { pkcs-9 1 }

EmailAddress ::=    IA5String (SIZE (1..ub-emailaddress-length))

-- naming data types --

Name ::= CHOICE { -- only one possibility for now --
    rdnSequence RDNSequence
}

RDNSequence ::=         SEQUENCE OF RelativeDistinguishedName

DistinguishedName ::=   RDNSequence

RelativeDistinguishedName ::= SET SIZE (1..MAX) OF AttributeTypeAndValue

-- Directory string type --

DirectoryString ::= CHOICE {
    teletexString   TeletexString   (SIZE (1..MAX)),
    printableString PrintableString (SIZE (1..MAX)),
    universalString UniversalString (SIZE (1..MAX)),
    utf8String      UTF8String      (SIZE (1..MAX)),
    bmpString       BMPString       (SIZE (1..MAX))
}

-- certificate and CRL specific structures begin here

Certificate ::= SEQUENCE {
    tbsCertificate      TBSCertificate,
    signatureAlgorithm  AlgorithmIdentifier,
    signature           BIT STRING
}

TBSCertificate ::= SEQUENCE {
    version             [0] Version DEFAULT v1,
    serialNumber            CertificateSerialNumber,
    signature               AlgorithmIdentifier,
    issuer                  Name,
    validity                Validity,
    subject                 Name,
    subjectPublicKeyInfo    SubjectPublicKeyInfo,
    issuerUniqueID      [1] IMPLICIT UniqueIdentifier OPTIONAL,
                        -- If present, version MUST be v2 or v3
    subjectUniqueID     [2] IMPLICIT UniqueIdentifier OPTIONAL,
                        -- If present, version MUST be v2 or v3
    extensions          [3] Extensions OPTIONAL
                        -- If present, version MUST be v3 --
}

Version ::= INTEGER { v1(0), v2(1), v3(2) }

CertificateSerialNumber ::= INTEGER

Validity ::= SEQUENCE {
    notBefore   Time,
    notAfter    Time
}

Time ::= CHOICE {
    utcTime     UTCTime,
    generalTime GeneralizedTime
}

UniqueIdentifier ::=  BIT STRING

SubjectPublicKeyInfo ::= SEQUENCE {
    algorithm           AlgorithmIdentifier,
    subjectPublicKey    BIT STRING  }

Extensions ::= SEQUENCE SIZE (1..MAX) OF Extension

Extension ::= SEQUENCE {
    extnID      OBJECT IDENTIFIER,
    critical    BOOLEAN DEFAULT FALSE,
    extnValue   OCTET STRING
                -- contains the DER encoding of an ASN.1 value
                -- corresponding to the extension type identified
                -- by extnID
}

-- CRL structures

CertificateList ::= SEQUENCE {
    tbsCertList         TBSCertList,
    signatureAlgorithm  AlgorithmIdentifier,
    signature           BIT STRING
}

TBSCertList ::= SEQUENCE {
    version                 Version OPTIONAL,
                                   -- if present, MUST be v2
    signature               AlgorithmIdentifier,
    issuer                  Name,
    thisUpdate              Time,
    nextUpdate              Time OPTIONAL,
    revokedCertificates     SEQUENCE OF SEQUENCE {
        userCertificate         CertificateSerialNumber,
        revocationDate          Time,
        crlEntryExtensions      Extensions OPTIONAL
                                -- if present, version MUST be v2
    }  OPTIONAL,
    crlExtensions           [0] Extensions OPTIONAL
                            -- if present, version MUST be v2
}

-- Version, Time, CertificateSerialNumber, and Extensions were
-- defined earlier for use in the certificate structure

AlgorithmIdentifier ::= SEQUENCE {
    algorithm   OBJECT IDENTIFIER,
    parameters  ANY DEFINED BY algorithm OPTIONAL
                -- contains a value of the type
                -- registered for use with the
                -- algorithm object identifier value
}

-- X.400 address syntax starts here

ORAddress ::= SEQUENCE {
    built-in-standard-attributes        BuiltInStandardAttributes,
    built-in-domain-defined-attributes  BuiltInDomainDefinedAttributes OPTIONAL,
    -- see also teletex-domain-defined-attributes
    extension-attributes                ExtensionAttributes OPTIONAL
}

-- Built-in Standard Attributes

BuiltInStandardAttributes ::= SEQUENCE {
    country-name                    CountryName OPTIONAL,
    administration-domain-name      AdministrationDomainName OPTIONAL,
    network-address             [0] IMPLICIT NetworkAddress OPTIONAL,
    -- see also extended-network-address
    terminal-identifier         [1] IMPLICIT TerminalIdentifier OPTIONAL,
    private-domain-name         [2] PrivateDomainName OPTIONAL,
    organization-name           [3] IMPLICIT OrganizationName OPTIONAL,
    -- see also teletex-organization-name
    numeric-user-identifier     [4] IMPLICIT NumericUserIdentifier OPTIONAL,
    personal-name               [5] IMPLICIT PersonalName OPTIONAL,
    -- see also teletex-personal-name
    organizational-unit-names [6] IMPLICIT OrganizationalUnitNames OPTIONAL
    -- see also teletex-organizational-unit-names
}

CountryName ::= [APPLICATION 1] CHOICE {
    x121-dcc-code           NumericString   (SIZE (ub-country-name-numeric-length)),
    iso-3166-alpha2-code    PrintableString (SIZE (ub-country-name-alpha-length))
}

AdministrationDomainName ::= [APPLICATION 2] CHOICE {
    numeric     NumericString   (SIZE (0..ub-domain-name-length)),
    printable   PrintableString (SIZE (0..ub-domain-name-length))
}

NetworkAddress ::= X121Address  -- see also extended-network-address

X121Address ::= NumericString (SIZE (1..ub-x121-address-length))

TerminalIdentifier ::= PrintableString (SIZE (1..ub-terminal-id-length))

PrivateDomainName ::= CHOICE {
    numeric     NumericString   (SIZE (1..ub-domain-name-length)),
    printable   PrintableString (SIZE (1..ub-domain-name-length)) }

OrganizationName ::= PrintableString (SIZE (1..ub-organization-name-length))
-- see also teletex-organization-name

NumericUserIdentifier ::= NumericString (SIZE (1..ub-numeric-user-id-length))

PersonalName ::= SET {
    surname                 [0] IMPLICIT PrintableString (SIZE (1..ub-surname-length)),
    given-name              [1] IMPLICIT PrintableString (SIZE (1..ub-given-name-length)) OPTIONAL,
    initials                [2] IMPLICIT PrintableString (SIZE (1..ub-initials-length)) OPTIONAL,
    generation-qualifier    [3] IMPLICIT PrintableString (SIZE (1..ub-generation-qualifier-length)) OPTIONAL
    -- see also teletex-personal-name
}

OrganizationalUnitNames ::= SEQUENCE SIZE (1..ub-organizational-units) OF OrganizationalUnitName
-- see also teletex-organizational-unit-names

OrganizationalUnitName ::= PrintableString (SIZE (1..ub-organizational-unit-name-length))

-- Built-in Domain-defined Attributes

BuiltInDomainDefinedAttributes ::= SEQUENCE SIZE (1..ub-domain-defined-attributes) OF BuiltInDomainDefinedAttribute

BuiltInDomainDefinedAttribute ::= SEQUENCE {
    type    PrintableString (SIZE(1..ub-domain-defined-attribute-type-length)),
    value   PrintableString (SIZE(1..ub-domain-defined-attribute-value-length))
}

-- Extension Attributes

ExtensionAttributes ::= SET SIZE (1..ub-extension-attributes) OF ExtensionAttribute

ExtensionAttribute ::= SEQUENCE {
    extension-attribute-type    [0] IMPLICIT INTEGER (0..ub-extension-attributes),
    extension-attribute-value   [1] ANY DEFINED BY extension-attribute-type
}

-- Extension types and attribute values

common-name INTEGER ::= 1

CommonName ::= PrintableString (SIZE (1..ub-common-name-length))

teletex-common-name INTEGER ::= 2

TeletexCommonName ::= TeletexString (SIZE (1..ub-common-name-length))

teletex-organization-name INTEGER ::= 3

TeletexOrganizationName ::= TeletexString (SIZE (1..ub-organization-name-length))

teletex-personal-name INTEGER ::= 4

TeletexPersonalName ::= SET {
    surname                 [0] IMPLICIT TeletexString (SIZE (1..ub-surname-length)),
    given-name              [1] IMPLICIT TeletexString (SIZE (1..ub-given-name-length)) OPTIONAL,
    initials                [2] IMPLICIT TeletexString (SIZE (1..ub-initials-length)) OPTIONAL,
    generation-qualifier    [3] IMPLICIT TeletexString (SIZE (1..ub-generation-qualifier-length)) OPTIONAL
}

teletex-organizational-unit-names INTEGER ::= 5

TeletexOrganizationalUnitNames ::= SEQUENCE SIZE (1..ub-organizational-units) OF TeletexOrganizationalUnitName

TeletexOrganizationalUnitName ::= TeletexString (SIZE (1..ub-organizational-unit-name-length))

pds-name INTEGER ::= 7

PDSName ::= PrintableString (SIZE (1..ub-pds-name-length))

physical-delivery-country-name INTEGER ::= 8

PhysicalDeliveryCountryName ::= CHOICE {
    x121-dcc-code           NumericString   (SIZE (ub-country-name-numeric-length)),
    iso-3166-alpha2-code    PrintableString (SIZE (ub-country-name-alpha-length))
}

postal-code INTEGER ::= 9

PostalCode ::= CHOICE {
    numeric-code    NumericString   (SIZE (1..ub-postal-code-length)),
    printable-code  PrintableString (SIZE (1..ub-postal-code-length))
}

physical-delivery-office-name INTEGER ::= 10

PhysicalDeliveryOfficeName ::= PDSParameter

physical-delivery-office-number INTEGER ::= 11

PhysicalDeliveryOfficeNumber ::= PDSParameter

extension-OR-address-components INTEGER ::= 12

ExtensionORAddressComponents ::= PDSParameter

physical-delivery-personal-name INTEGER ::= 13

PhysicalDeliveryPersonalName ::= PDSParameter

physical-delivery-organization-name INTEGER ::= 14

PhysicalDeliveryOrganizationName ::= PDSParameter

extension-physical-delivery-address-components INTEGER ::= 15

ExtensionPhysicalDeliveryAddressComponents ::= PDSParameter

unformatted-postal-address INTEGER ::= 16

UnformattedPostalAddress ::= SET {
    printable-address   SEQUENCE SIZE (1..ub-pds-physical-address-lines) OF PrintableString (SIZE (1..ub-pds-parameter-length)) OPTIONAL,
    teletex-string      TeletexString (SIZE (1..ub-unformatted-address-length)) OPTIONAL
}

street-address INTEGER ::= 17

StreetAddress ::= PDSParameter

post-office-box-address INTEGER ::= 18

PostOfficeBoxAddress ::= PDSParameter

poste-restante-address INTEGER ::= 19

PosteRestanteAddress ::= PDSParameter

unique-postal-name INTEGER ::= 20

UniquePostalName ::= PDSParameter

local-postal-attributes INTEGER ::= 21

LocalPostalAttributes ::= PDSParameter

PDSParameter ::= SET {
    printable-string    PrintableString (SIZE(1..ub-pds-parameter-length)) OPTIONAL,
    teletex-string      TeletexString   (SIZE(1..ub-pds-parameter-length)) OPTIONAL
}

extended-network-address INTEGER ::= 22

ExtendedNetworkAddress ::= CHOICE {
    e163-4-address SEQUENCE {
        number      [0] IMPLICIT NumericString (SIZE (1..ub-e163-4-number-length)),
        sub-address [1] IMPLICIT NumericString (SIZE (1..ub-e163-4-sub-address-length)) OPTIONAL
    },
    psap-address    [0] IMPLICIT PresentationAddress
}

PresentationAddress ::= SEQUENCE {
    pSelector   [0] EXPLICIT OCTET STRING OPTIONAL,
    sSelector   [1] EXPLICIT OCTET STRING OPTIONAL,
    tSelector   [2] EXPLICIT OCTET STRING OPTIONAL,
    nAddresses  [3] EXPLICIT SET SIZE (1..MAX) OF OCTET STRING
}

terminal-type  INTEGER ::= 23

TerminalType ::= INTEGER {
    telex           (3),
    teletex         (4),
    g3-facsimile    (5),
    g4-facsimile    (6),
    ia5-terminal    (7),
    videotex        (8)
} (0..ub-integer-options)

-- Extension Domain-defined Attributes

teletex-domain-defined-attributes INTEGER ::= 6

TeletexDomainDefinedAttributes ::= SEQUENCE SIZE (1..ub-domain-defined-attributes) OF TeletexDomainDefinedAttribute

TeletexDomainDefinedAttribute ::= SEQUENCE {
    type    TeletexString   (SIZE (1..ub-domain-defined-attribute-type-length)),
    value   TeletexString   (SIZE (1..ub-domain-defined-attribute-value-length))
}

--  specifications of Upper Bounds MUST be regarded as mandatory
--  from Annex B of ITU-T X.411 Reference Definition of MTS Parameter
--  Upper Bounds

-- Upper Bounds
ub-name                                     INTEGER ::= 32768
ub-common-name                              INTEGER ::= 64
ub-locality-name                            INTEGER ::= 128
ub-state-name                               INTEGER ::= 128
ub-organization-name                        INTEGER ::= 64
ub-organizational-unit-name                 INTEGER ::= 64
ub-title                                    INTEGER ::= 64
ub-serial-number                            INTEGER ::= 64
ub-match                                    INTEGER ::= 128
ub-emailaddress-length                      INTEGER ::= 255
ub-common-name-length                       INTEGER ::= 64
ub-country-name-alpha-length                INTEGER ::= 2
ub-country-name-numeric-length              INTEGER ::= 3
ub-domain-defined-attributes                INTEGER ::= 4
ub-domain-defined-attribute-type-length     INTEGER ::= 8
ub-domain-defined-attribute-value-length    INTEGER ::= 128
ub-domain-name-length                       INTEGER ::= 16
ub-extension-attributes                     INTEGER ::= 256
ub-e163-4-number-length                     INTEGER ::= 15
ub-e163-4-sub-address-length                INTEGER ::= 40
ub-generation-qualifier-length              INTEGER ::= 3
ub-given-name-length                        INTEGER ::= 16
ub-initials-length                          INTEGER ::= 5
ub-integer-options                          INTEGER ::= 256
ub-numeric-user-id-length                   INTEGER ::= 32
ub-organization-name-length                 INTEGER ::= 64
ub-organizational-unit-name-length          INTEGER ::= 32
ub-organizational-units                     INTEGER ::= 4
ub-pds-name-length                          INTEGER ::= 16
ub-pds-parameter-length                     INTEGER ::= 30
ub-pds-physical-address-lines               INTEGER ::= 6
ub-postal-code-length                       INTEGER ::= 16
ub-pseudonym                                INTEGER ::= 128
ub-surname-length                           INTEGER ::= 40
ub-terminal-id-length                       INTEGER ::= 24
ub-unformatted-address-length               INTEGER ::= 180
ub-x121-address-length                      INTEGER ::= 16

-- Note - upper bounds on string types, such as TeletexString, are
-- measured in characters.  Excepting PrintableString or IA5String, a
-- significantly greater number of octets will be required to hold
-- such a value.  As a minimum, 16 octets, or twice the specified
-- upper bound, whichever is the larger, should be allowed for

-- TeletexString.  For UTF8String or UniversalString at least four
-- times the upper bound should be allowed.

END
"""

_X509_DECODER = asn1tools.compile_string(_X509_ASN1, codec="der")


# obtidos em dpc.acue2020.tse.jus.br
_AC_RAIZ_UE_PEMS = [
    # acurna.crt
    """
MIID+jCCA1ygAwIBAgIBAzAKBggqhkjOPQQDBDCBgjELMAkGA1UEBhMCQlIxDDAK
BgNVBAoTA1RTRTEMMAoGA1UECxMDU1RJMRMwEQYDVQQDEwpBQyBSQUlaIFVFMQsw
CQYDVQQIEwJERjERMA8GA1UEBxMIQnJhc2lsaWExIjAgBgkqhkiG9w0BCQEWE2Fj
cmFpenVlQHRzZS5qdXMuYnIwHhcNMTEwNzIyMjE1OTU3WhcNMjYwNzE4MjE1OTU3
WjB9MRAwDgYDVQQDEwdBQyBVUk5BMQswCQYDVQQIEwJERjELMAkGA1UEBhMCQlIx
IDAeBgkqhkiG9w0BCQEWEWFjdXJuYUB0c2UuanVzLmJyMQwwCgYDVQQKEwNUU0Ux
DDAKBgNVBAsTA1NUSTERMA8GA1UEBxMIQnJhc2lsaWEwgZswEAYHKoZIzj0CAQYF
K4EEACMDgYYABACBR0E65ux46ll8Z41Fi0QJf+LWQqUZDI2wIvB4+F9vHqrw0/tb
6pasdXwwxxdRia5oI21UrKsN2f0VxCtWGPAzzwHPPXSY4w9bSIg/evLDXFZ9QNKK
EWt83xzz1U6nsd2H+XI2sNSOWQS485ZYQ7nnThRgPhRsYsbCKb6Gmt7JTNudkqOC
AYIwggF+MAwGA1UdEwQFMAMBAf8wga8GA1UdIwSBpzCBpIAUhmiDe7vjSM0ZthAw
pInV395nQsChgYikgYUwgYIxCzAJBgNVBAYTAkJSMQwwCgYDVQQKEwNUU0UxDDAK
BgNVBAsTA1NUSTETMBEGA1UEAxMKQUMgUkFJWiBVRTELMAkGA1UECBMCREYxETAP
BgNVBAcTCEJyYXNpbGlhMSIwIAYJKoZIhvcNAQkBFhNhY3JhaXp1ZUB0c2UuanVz
LmJyggEBMB0GA1UdDgQWBBTNqvSylwGz8N6ytUJYWUptNK2kijALBgNVHQ8EBAMC
AYYwPAYDVR0fBDUwMzAxoC+gLYYraHR0cDovL2xjci5hY3JhaXp1ZS50c2UuanVz
LmJyL2FjcmFpenVlLmNybDBSBgNVHSAESzBJMEcGAwAAADBAMD4GCCsGAQUFBwIB
FjJodHRwOi8vZHBjLmFjcmFpenVlLnRzZS5qdXMuYnIvRFBDLVBDLUFDUkFJWlVF
LnBkZjAKBggqhkjOPQQDBAOBiwAwgYcCQS2Qnvfn3wF8Ft96nAjZH5tp/0VKwp0j
iJYy1+7Bx5PB94lW6D7Hqvfe6XClC9faSrNTQL1XFdZg2yw/hMROUb2uAkIBe8l4
fiGIaXNVTLstkxNGYoXCjJvGtBc1zeFBRXKA3S95lskEMn8QJ06vYRK6PiUu5foM
yaLcujRjcz9Mb7zpTfo=
""",
    # acue2020.crt
    """
MIIDITCCAoegAwIBAgIBBTAMBgorBgEEAYLcLAIBMIGCMRMwEQYDVQQDDApBQyBV
Uk5BIHYyMQswCQYDVQQIDAJERjELMAkGA1UEBhMCQlIxIjAgBgkqhkiG9w0BCQEW
E2FjdXJuYXYyQHRzZS5qdXMuYnIxDDAKBgNVBAoMA1RTRTEMMAoGA1UECwwDU1RJ
MREwDwYDVQQHDAhCcmFzaWxpYTAeFw0yMTA3MDUyMTMxNTZaFw0zNzA3MDEyMTMx
NTZaMIGBMRIwEAYDVQQDDAlBQyBVRTIwMjAxCzAJBgNVBAgMAkRGMQswCQYDVQQG
EwJCUjEiMCAGCSqGSIb3DQEJARYTYWN1ZTIwMjBAdHNlLmp1cy5icjEMMAoGA1UE
CgwDVFNFMQwwCgYDVQQLDANTVEkxETAPBgNVBAcMCEJyYXNpbGlhMFMwDAYKKwYB
BAGC3CwCAQNDAF09dk0RI6kU77+TiS2ztj0vPF03oPFKLTbUSQXMdCi5dDVRcd94
wqBk5jCzCLBhpH+wvVVxX8W2lBm/yS7VcK65AaOB8DCB7TAMBgNVHRMEBTADAQH/
MAsGA1UdDwQEAwIBBjAdBgNVHQ4EFgQUvLNUXe7qQy4egy6BKDy4rpSOQAswHwYD
VR0jBBgwFoAU0CVmxJEDSzqTE7MHSSHsqbUA4h8wPAYDVR0fBDUwMzAxoC+gLYYr
aHR0cDovL2xjci5hY3VybmF2Mi50c2UuanVzLmJyL2FjdXJuYXYyLmNybDBSBgNV
HSAESzBJMEcGAwAAADBAMD4GCCsGAQUFBwIBFjJodHRwOi8vZHBjLmFjdXJuYXYy
LnRzZS5qdXMuYnIvRFBDLVBDLUFDVVJOQVYyLlBERjAMBgorBgEEAYLcLAIBA4GF
ADuPH84sRDCnd7vmSDb3ae7qtPoUCcPbeOJb3zFtArAUm6ki7bV0Fa0jUri4LtEm
XYgrhOETAvqaRBlBk2vRH409gRbpHpMf9cvzgoMGAp+ShXHwlZ4m6XJuFXi77hMc
qGvoUFpGzp0yXzbP1uK1QMvfyVakWpczXQnvS3zay18ik9NFAA==
""",
    # acue2022.crt
    """
MIIDITCCAoegAwIBAgIBCDAMBgorBgEEAYLcLAIBMIGCMRMwEQYDVQQDDApBQyBV
Uk5BIHYyMQswCQYDVQQIDAJERjELMAkGA1UEBhMCQlIxIjAgBgkqhkiG9w0BCQEW
E2FjdXJuYXYyQHRzZS5qdXMuYnIxDDAKBgNVBAoMA1RTRTEMMAoGA1UECwwDU1RJ
MREwDwYDVQQHDAhCcmFzaWxpYTAeFw0yMzAyMjgxMzQ2NDlaFw0zOTAyMjQxMzQ2
NDlaMIGBMRIwEAYDVQQDDAlBQyBVRTIwMjIxCzAJBgNVBAgMAkRGMQswCQYDVQQG
EwJCUjEiMCAGCSqGSIb3DQEJARYTYWN1ZTIwMjJAdHNlLmp1cy5icjEMMAoGA1UE
CgwDVFNFMQwwCgYDVQQLDANTVEkxETAPBgNVBAcMCEJyYXNpbGlhMFMwDAYKKwYB
BAGC3CwCAQNDADcTiMAO2BJpyn3QVzU5bKqWqCBe/X4uls8WVXtSR15k6Sietkdo
S87iRk2Im3FVzsivJPK+TSGho6sVgFzfVdTsAKOB8DCB7TAMBgNVHRMEBTADAQH/
MAsGA1UdDwQEAwIBBjAdBgNVHQ4EFgQUu3xRfylKW5b5v2qWTE8lWnVfaYowHwYD
VR0jBBgwFoAU0CVmxJEDSzqTE7MHSSHsqbUA4h8wPAYDVR0fBDUwMzAxoC+gLYYr
aHR0cDovL2xjci5hY3VybmF2Mi50c2UuanVzLmJyL2FjdXJuYXYyLmNybDBSBgNV
HSAESzBJMEcGAwAAADBAMD4GCCsGAQUFBwIBFjJodHRwOi8vZHBjLmFjdXJuYXYy
LnRzZS5qdXMuYnIvRFBDLVBDLUFDVVJOQVYyLlBERjAMBgorBgEEAYLcLAIBA4GF
AChtHrhxscJ/SiePj3cCI/aPt5uJxC43PR6FjNENukBYxwkkWvFRbPblU/2muJZM
82ezEJtfcQ+3hWHoIZXKnkdTASSo0OX4TwykkFSb3/jX+D65ePsKUPGmYyWzt05A
+appfWxFCmWlib09waOnIQ6NmmrNPW8GGgaCiU54Xc3mElhTAA==
""",
]

_CHAVES_RAIZ = carrega_chaves_pems(_AC_RAIZ_UE_PEMS)
