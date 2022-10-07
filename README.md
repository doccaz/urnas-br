# Sobre o projeto 

Com as recentes polêmicas sobre a apuração de resultados do primeiro turno da eleição de 2022, comecei a acompanhar os resultados
em https://resultados.tse.jus.br, que oferece uma opção para baixar os boletins de urna (BU) individualmente. Numa conversa informal, surgiu a idéia de baixar em lote estes arquivos para fazermos análises.

**IMPORTANTE 1:** Trata-se de um projeto EDUCACIONAL e sem fins políticos. Apenas vi um problema interessante e resolvi estudar como resolvê-lo. Não me responsabilizo pelo que for feito com estes dados, ou por informações incorretas. Use por sua conta e risco.

**IMPORTANTE 2:** Apesar de ter criado uma opção para baixar todas as UFs de uma vez, **NÃO FAÇA ISSO**. A quantidade de arquivos é **IMENSA** e pode causar problemas para os servidores do TSE. Se for baixar, baixe uma UF por vez!


# Legal, como posso ajudar?

Eu não sou estatístico nem muito menos um data scientist. Se tiver o expertise e queira analisar os dados, esteja à vontade!

Se quiser corrigir alguma informação incorreta sobre os formatos/estrutura, ou erros de programação, abra um issue e/ou pull request!

Sugestões são bem-vindas.


# Por onde começar?

Analisando a estrutura do site, percebi que a aplicação web se utiliza de algumas consultas prontas, trazidas em formato JSON.
Estas consultas possuem desde dados das eleições, candidatos e partidos, municípios e até os dados individuais de zonas e seções.

Depois de muita análise e engenharia reversa, consegui criar um mapa lógico do que precisaria para obter o arquivo .bu de cada urna, cruzando estes dados.

Depois de determinar os padrões para nomenclatura dos arquivos, apenas gerei um script simples em BASH para baixar os JSON principais para cada UF.


Para tanto, os passos iniciais ficaram assim:

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

