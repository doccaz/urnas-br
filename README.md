# Sobre o projeto 

Com as recentes polêmicas sobre a apuração de resultados do primeiro turno da eleição de 2022, comecei a acompanhar os resultados
em https://resultados.tse.jus.br, que oferece uma opção para baixar os boletins de urna (BU) individualmente. Numa conversa informal, surgiu a idéia de baixar em lote estes arquivos para fazermos análises.

**IMPORTANTE 1:** Trata-se de um projeto EDUCACIONAL e sem fins políticos. Apenas vi um problema interessante e resolvi estudar como resolvê-lo. Não me responsabilizo pelo que for feito com estes dados, ou por informações incorretas. Use por sua conta e risco.

**IMPORTANTE 2:** Apesar de ter criado uma opção para baixar todas as UFs de uma vez, **NÃO FAÇA ISSO**. A quantidade de arquivos é **IMENSA** (CENTENAS DE MILHARES de arquivos) e pode causar problemas para os servidores do TSE. Se for baixar, baixe uma UF por vez!


# Legal, como posso ajudar?

Eu não sou estatístico nem muito menos um data scientist. Se tiver o expertise e queira analisar os dados, esteja à vontade!

Se quiser corrigir alguma informação incorreta sobre os formatos/estrutura, ou erros de programação, abra um issue e/ou pull request!

Sugestões são bem-vindas.


# Por onde começar?

Analisando a estrutura do site, percebi que a aplicação web se utiliza de algumas consultas prontas, trazidas em formato JSON.
Estas consultas possuem desde dados das eleições, candidatos e partidos, municípios e até os dados individuais de zonas e seções.

Depois de muita análise e engenharia reversa, consegui criar um mapa lógico do que precisaria para obter o arquivo .bu de cada urna, cruzando estes dados.

Depois de determinar os padrões para nomenclatura dos arquivos, apenas gerei um script simples em BASH para baixar os JSON principais para cada UF.



# Utilização do script

O script precisa de alguns parâmetros para ser executado:

```
erico@suselab-erico:/data/urnas-br> ./baixa_por_uf.py -h
Uso: 
        -g|--geral=<identificador geral>                Identificador geral (ex: ele2022)
        -p|--pleito=<id do pleito>                      Identificador do Pleito (ex: 406)
        -e|--eleicao=<id da eleição>                    Identificador da Eleição (ex: 544)
        -u|--uf=<estado>                                Estado a consultar
        -a|--all                                        Baixa todos os estados
        -b|--bu                                         Baixa apenas os arquivos de BU, ignorando os outros tipos
        -i|--imgbu                                      Baixa apenas os arquivos de espelho de BU, ignorando os outros tipos
        -z|--logjez                                     Baixa apenas os arquivos de log, ignorando os outros tipos
        -r|--rdv                                        Baixa apenas os arquivos de registro de voto, ignorando os outros tipos
        -v|--vscmr                                      Baixa apenas os arquivos de assinaturas, ignorando os outros tipos
        -l|--list                                       Lista os identificadores disponíveis na base do TSE
        -h|--help                                       Exibe a ajuda

```


Utilize a opção '-l' (ou --list) para obter a lista com todos os identificadores de eleição disponíveis na base do TSE:

```
erico@suselab-erico:/data/urnas-br> ./baixa_por_uf.py -l
* iniciando download: https://resultados.tse.jus.br/oficial/comum/config/ele-c.json (4681 bytes)
[OK] download concluido: https://resultados.tse.jus.br/oficial/comum/config/ele-c.json status: 200 (4681 bytes, 0 segundos)

IDENTIFICADOR GERAL: ele2022
==============================================


---> PLEITO: 406
CODIGO: 546 - Eleição Ordinária Estadual - 2022 1&#186; Turno
CODIGO: 544 - Eleição Ordinária Federal - 2022 1&#186; Turno
CODIGO: 548 - Eleição Ordinária Municipal - 2022 - 02/10/2022 1&#186; Turno

---> PLEITO: 407
CODIGO: 571 - Eleição Suplementar - Vilhena
CODIGO: 563 - Eleição Suplementar - Canoinhas
CODIGO: 574 - Eleição Suplementar - Joaquim Nabuco
CODIGO: 562 - Eleição Suplementar - Pesqueira
CODIGO: 547 - Eleição Ordinária Estadual - 2022 2&#186; Turno
CODIGO: 565 - Eleição Suplementar - Cerro Grande
CODIGO: 566 - Eleição Suplementar - Entre Rios Do Sul
CODIGO: 564 - Eleição Suplementar - Cachoeirinha
CODIGO: 572 - Eleição Suplementar - Pinhalzinho
CODIGO: 545 - Eleição Ordinária Federal - 2022 2&#186; Turno

---> PLEITO: 421
CODIGO: 581 - Eleição Suplementar - Maraial
```

Logo, se quisermos por exemplo baixar os dados de urna para o DF, da eleição 545 (Federal, segundo turno), fazemos:

```
erico@suselab-erico:/data/urnas-br> ./baixa_por_uf.py -g ele2022 -p 407 -e 545 -u df
```

e o download irá começar. Pressione CTRL-C para interromper se necessário. Execuções subsequentes pulam os arquivos já baixados e continuam de onde parou o processo.

Por padrão, baixamos todos os arquivos disponíveis para cada urna (são 5: logjez, bu, imgbu, rdv e vscmr). Caso queira limitar a um ou mais tipos, basta especificar os flags correspondentes.

Por exemplo, para baixar APENAS os boletins de urna para o estado AMAZONAS da eleição 2022 do segundo turno (federal):

```
erico@suselab-erico:/data/urnas-br> ./baixa_por_uf.py -g ele2022 -p 407 -e 545 -u am --bu
```



# Ok, mas como funciona tudo por trás e como você encontrou as informações???

Os passos para se obter os dados de uma eleição ficaram assim:

## 1. Obter a relação de pleitos

URL de exemplo: https://resultados.tse.jus.br/oficial/comum/config/ele-c.json

---> daqui vem o 406 (eleições gerais 2022)
```
{
   "c" : "ele2022",
   "dg" : "02/10/2022",
   "f" : "O",
   "hg" : "21:18:55",
   "pl" : [
      {
         "cd" : "406",
         "cdpr" : "395",
         "dt" : "02/10/2022",
         "dtlim" : "02/09/2024",
         ...
```

---> daqui vem o 544 (eleição federal 1o. turno)
```
              "cd" : "544",
               "cdt2" : "545",
               "nm" : "Eleição Ordinária Federal - 2022 1&#186; Turno",
               "t" : "1",
               "tp" : "8"
...
```

---> daqui vem o 546 (eleição estadual 1o. turno)
```
               "cd" : "546",
               "cdt2" : "547",
               "nm" : "Eleição Ordinária Estadual - 2022 1&#186; Turno",
               "t" : "1",
               "tp" : "1"
               ...
```

---> daqui vem o 548 (eleição municipal)
```
               "cd" : "548",
               "cdt2" : "",
               "nm" : "Eleição Ordinária Municipal - 2022 - 02/10/2022 1&#186; Turno",
               "t" : "1",
               "tp" : "3"
...
```

               
## 2. Obter a lista de municípios, zonas e seções do estado

URL de exemplo: https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/config/ap/ap-p000406-cs.json

onde:

- oficial = base de dados
- ele2022 = eleições de 2022
- arquivo-urna = ...
- 406 = pleito (eleições gerais de 2022)
- config = ...
- ap = estado (Amapá)
- ap-p000406-cs.json = arquivo de dados

onde:
- ap = Amapá
- p000406 = pleito 406 (eleições gerais de 2022)
- cs = ?

Para todos:
```
ESTADOS="ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to"
for f in ${ESTADOS}; do wget https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/config/${f}/${f}-p000406-cs.json; done
```


## 3. Obter lista de urnas por estado/município/seção (com hashes e nomes de arquivos)

URL de exemplo: https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/p000406-ap-m06050-z0002-s0824-aux.json

```
{
   "dg" : "02/10/2022",
   "ds" : "",
   "f" : "O",
   "hashes" : [
      {
         "dr" : "02/10/2022",
         "ds" : "",
         "hash" : "534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d",
         "hr" : "19:20:08",
         "nmarq" : [
            "o00406-0605000020824.logjez",
            "o00406-0605000020824.rdv",
            "o00406-0605000020824.bu",
            "o00406-0605000020824.vscmr",
            "o00406-0605000020824.imgbu"
         ],
         "st" : "Totalizado"
      }
   ],
   "hg" : "23:27:25",
   "st" : "Totalizada"
}
```

----> a lista "hashes" pode conter mais de um registro de urna naquela seção


Breakdown dos parâmetros:

- 406 = código do pleito ( o mesmo para o 1o turno pro BR inteiro?)
- ap = Amapá
- 06050 = código do município (Macapá)
- 0002 = zona eleitoral
- 0824 = seção


nome do arquivo: p000406-ap-m06050-z0002-s0824-aux.json

- p000406 = pleito 406 (eleições gerais de 2022)
- ap = Amapá
- m06050 = município de Macapá
- z0002 = zona eleitoral 0002
- s0824 = seção 0824


## 4. Obter arquivos da cada urna

URL de exemplo: https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.logjez

*** também aceita as extensões:
- bu (boletim de urna)
- rdv (registro de voto)
- vscmr (???)
- imgbu (imagem de boletim de urna?)
- logjez = identificado como 7-zip, contém um arquivo logd.dat, que é o log em formato texto


* Composição da URL:

- oficial = base de dados
- ele2022 = eleição
- arquivo-urna = tipo
- 406 = pleito (406 para 1o. turno?)
- dados = ...
- ap = Amapá
- 06050 = município de Macapá
- 0002 = zona eleitoral
- 0824 = seção
- 534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d = hash obtido no arquivo -aux.json (SHA2?)
- o00406-0605000020824.logjez = nome do arquivo

onde:

- o00406 = pleito
- 06050 = município
- 0002 = zona eleitoral
- 0824 = seção
- .logjez = extensão


Logo, neste caso é necessário baixar 5 URLs:

- https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.logjez

- https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.rdv

- https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.bu

- https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.imgbu

- https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/406/dados/ap/06050/0002/0824/534f753676357056516e4a42384e376c77544b32533257562b794a2d4968375a6e7a654f504b6746762b493d/o00406-0605000020824.vscmr


# Baixa de arquivos

Cada zona pode ter N seções, e cada seção tem *pelo menos* uma urna. Cada urna tem 5 arquivos de dados. 

Logo, a conta começa a ficar alta: se um estado tiver, por exemplo, 5000 seções, com 5000 urnas e 5 arquivos de cada... já são 25.000 arquivos para baixar (fora os arquivos JSON de controle e dados de municípios para cruzamento).

Note que para se chegar a cada um dos passos acima, é necessário baixar um JSON, entender seu formato e utilizar seus dados para baixar o próximo JSON que trará a próxima informação, até chegar no nível do boletim de urna.

Aí temos um problema grande para resolver: como baixar esta massa enorme de arquivos de forma ordenada? 

O programa "baixa_por_uf.py" atende exatamente este problema.

Para começar, é preciso deixar claro que tomei alguns "atalhos", pois o interesse não era recriar totalmente a base do TSE, mas sim buscar os BUs com votos do primeiro turno das eleições de 2022. Logo, alguns valores estão "hard-coded" para facilitar.


# Processamento dos dados obtidos

Uma vez obtidos todos os dados, é hora de interpretar os arquivos.

Dos 5 arquivos baixados, 2 chamam a atenção: os de extensão .logjez e .bu. 

O arquivo .logjez é um arquivo compactado no formato 7-zip. Dentro dele, encontramos um log em formato texto da urna. Apesar de ter (muitas) informações interessantes sobre o funcionamento do equipamento da urna, inclusive os votos (anonimizados) entrados pelos eleitores, não possui dados sobre a quantidade de eleitores habilitados para aquela seção versus a quantidade de eleitores que votaram (que é um dos pontos questionados). O formato também não ajuda na hora de interpretar programaticamente.

O arquivo .bu é o boletim final da urna. Ele contém as informações que precisamos, mas está em formato binário (ASN.1). Depois de quebrar a cabeça tentando fazer a engenharia reversa parcial dos campos, encontrei uma documentação oficial(!) com os formatos dos arquivos. Note que trata-se de documentação *PÚBLICA*, baixada da URL https://www.tre-mt.jus.br/eleicoes/eleicoes-2022/documentacao-tecnica-do-software-da-urna-eletronica .

Para conveniência, deixei uma cópia desta documentação no diretório "doc".

Assim nasceu o programa "processa_bu_csv.py", que além de interpretar os campos do BU, cruza os dados obtidos anteriormente e gera um arquivo .CSV com o resumo dos votos de cada urna. O formato final ficou assim:

```
"UF","cod_municipio","municipio","zona","secao","eleitores_aptos","candidato","quantidade_votos"
ap,6050,"MACAPÁ",00002,0001,205,12,11
ap,6050,"MACAPÁ",00002,0001,205,13,75
ap,6050,"MACAPÁ",00002,0001,205,15,17
ap,6050,"MACAPÁ",00002,0001,205,22,61
ap,6050,"MACAPÁ",00002,0001,205,30,1
ap,6050,"MACAPÁ",00002,0001,205,BRANCO,1
ap,6050,"MACAPÁ",00002,0001,205,NULO,2
```

onde temos, na sequência:
- UF = estado onde se localiza a urna
- cod_municipio = código do TSE que identifica o município
- municipio = nome do município
- zona = a zona eleitoral à qual pertence a urna
- secao = seção eleitoral
- eleitores_aptos = quantidade de eleitores registrados e aptos a votar naquela seção
- candidato = número do candidato (não coloquei nome nem partido -- precisa?)
- quantidade_votos = quantidade de votos registrados para aquele candidato

os votos brancos e nulos aparecem como um "candidato" também.


# Bônus: Relação de candidatos e resultados simplificados de cada estado

URL de exemplo: https://resultados.tse.jus.br/oficial/ele2022/546/dados-simplificados/ap/ap-c0007-e000546-r.json

onde:

- oficial = base de dados
- ele2022 = eleições de 2022
- 546 = eleição federal de 2022 (ver tópico 1)
- dados-simplificados = ...
- ap = estado (Amapá)

nome do arquivo de candidatos: ap-c0007-e000546-r.json

onde:
- ap = estado (Amapá)
- c0007 = cargo, de acordo com o ele-c.json (tópico 1)
```
               {
                           "cd" : "7",
                           "ds" : "Deputado Estadual",
                           "tp" : "2"
                }
```

- e000546 = eleição estadual, de acordo com ele-c.json (tópico 1)
```
               "cd" : "546",
               "cdt2" : "547",
               "nm" : "Eleição Ordinária Estadual - 2022 1&#186; Turno",
               "t" : "1",
               "tp" : "1"
```
- r = resultados(?)

Logo, para presidente no estado do Amapá:

URL de exemplo: https://resultados.tse.jus.br/oficial/ele2022/544/dados-simplificados/ap/ap-c0001-e000544-r.json

e nos resultados:
- vap = votos apurados (187621)
- pvap = percentual de votos apurados (43,41)
- pst = total de seções totalizadas (100)


Para baixar de todos os estados:
```
ESTADOS="ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to"
for f in ${ESTADOS}; do wget https://resultados.tse.jus.br/oficial/ele2022/544/dados-simplificados/${f}/${f}-c0001-e000544-r.json; done
```

# Bônus: codificação do QR Code no boletim de urna


Existe um documento oficial do TSE (https://www.tse.jus.br/hotsites/catalogo-publicacoes/pdf/qr-code-no-boletim-de-urna-1-4.pdf) em que é mostrado parte por parte como é formado o texto que está contido no Boletim de Urna.

Decodificando o próprio exemplo citado no documento, temos:

```
QRBU:1:1 ORIG:VOTA PROC:2000 DTPL:20161002 PLEI:2100 TURN:1 FASE:S UNFE:AC MUNI:1392 ZONA:9 SECA:31 IDUE:1760649 IDCA:529951844372447180336660 VERS:5.22.0.1 VRQR:4.0 LOCA:4 APTO:40 COMP:10 FALT:30 HBMA:4 DTAB:20161002 HRAB:173449 DTFC:20161002 HRFC:180133 IDEL:2101 CARG:13 TIPO:1 VERC:201606281643 PART:91 91001:1 91004:1 LEGP:0 TOTP:2 PART:92 92003:1 92004:1 92005:1 LEGP:0 TOTP:3 PART:93 93004:1 93005:1 LEGP:0 TOTP:2 PART:94 94001:2 LEGP:0 TOTP:2 NOMI:9 LEGC:0 BRAN:1 NULO:0 TOTC:10 CARG:11 TIPO:0 VERC:201606281643 91:2 92:2 93:3 97:1 NOMI:8 BRAN:2 NULO:0 TOTC:10 HASH:69720370FEF82D1235846B6500408F48068DF564553DEEAD273CA20BCE959A3791281379FF96B28755B15DFB7254EE6937C70BE69CB941D69AF73C57622DAA27 ASSI:D4A834C84DBE93DAF86CCF7B1D9743796FB478ED954C44896F551E53D3F1A9F7CCB2769564CDA02585070F313C003F8C046AD49C2250375B6818A76BD5842E0D
```

Basicamente, são colocadas as mesmas informações que estão no boletim impresso, o hash e a assinatura, precedidos de descritores.

Os arquivos .imgbu contém exatamente o que é enviado para o módulo de impressora, incluindo todos os caracteres de controle (geralmente comandos ESC/P2, mas que variam de acordo com o fabricante do módulo de impressora usado na urna). A imagem do QRCode está presente como bitmap no final do arquivo, mas codificado de acordo com o que o fabricante exige. Não tenho informação de qual módulo/firmware é utilizado nas urnas, mas provavelmente é algum módulo baseado na IM453H da própria Diebold.


