# Memorando · Onde intervir na linha em Juiz de Fora

**Para:** segurança operacional e relação com comunidades (MRS); Secretaria de Mobilidade (PJF)
**Assunto:** prioridade dos trechos para a vedação e as travessias do plano de investimentos
**Base:** atropelamentos de 2011 a 2025 declarados à ANTT (RAAF), Censo 2022, CNEFE 2022 e INEP 2023. Projeto independente, sem vínculo com a MRS ou a ANTT.

## Recomendação

O plano de investimentos da renovação da concessão prevê cerca de 22 km de vedação em Juiz de Fora até 2027 e melhorias em 9 travessias de pedestres, com os pontos a definir ([Tribuna de Minas, 26/03/2023](https://tribunademinas.com.br/noticias/cidade/26-03-2023/mrs-elabora-estudos-tecnicos-para-construcao-de-viadutos-em-juiz-de-fora.html)). Os dados apontam para três trechos de 1 km, em ordem:

| Prioridade | Trecho | Atropelamentos (óbitos) | Esperado para o movimento | Onde acontece | Intervenção |
|---|---|---|---|---|---|
| 1 | km 274 | 25 (16) | 11,3 | 68% em passagem em nível | Tratar a passagem: travessia de pedestre separada, sinalização, cancela. Ruas que cruzam a linha: Pinto de Moura, Espírito Santo |
| 2 | km 275 | 32 (11) | 21,9 | 78% em passagem em nível | Idem, na Rua Halfeld (Praça da Estação) |
| 3 | km 273 | 17 (8) | 10,1 | 76% fora da passagem | Vedação com travessia segura no caminho que as pessoas já fazem, perto da Rua João Luiz de Barros |

Em seguida vem o **km 265**, perto do Retiro: 9 atropelamentos (5 óbitos) onde se esperavam 2,2, quase todos fora da passagem em nível. Ele não aparece numa contagem simples.

Duas das três passagens em nível que o plano manda melhorar (Rua João Luiz de Barros e Praça da Estação) caem nesses trechos.

## Quanto vale

Os três trechos somam **1,5 atropelamento por ano** acima do que trechos com o mesmo movimento têm. Com a letalidade de 54%, são **0,8 óbito por ano**, ou cerca de **R$ 970 mil por ano** em custo social. Por óbito, o valor é o custo de um acidente rodoviário com morte do Ipea (R$ 646,7 mil em 2014), corrigido pelo IPCA. É um piso: levar o trecho à média. Uma vedação bem feita pode ganhar mais.

## Por que não a contagem simples

O centro de Juiz de Fora é comercial. O km 275 tem 2.414 endereços de comércio e serviço a até 500 m da linha; fora o km 276 (1.269), os outros trechos urbanos têm de 100 a 700. A regressão mostra que o comércio, e não o número de moradores, explica onde os atropelamentos acontecem. Por isso cada trecho é comparado com o esperado para o seu movimento, pelo método empírico-bayesiano do *Highway Safety Manual*. É assim que o km 276, 3º em contagem, cai para 5º: 19 casos contra 17,3 esperados.

## Quanto confiar

- **O acidente não tem coordenada.** O km foi posto no traçado com âncoras deduzidas dos próprios registros. A posição erra de 100 a 300 m, por isso o trecho tem 1 km e a rua é a provável.
- **O ranking aguenta.** Com ±200 m de erro, os km 274 e 273 ficam entre os três primeiros em 200 de 200 sorteios, e o 275 em 186. Com faixas de 300, 500 ou 800 m, os cinco primeiros são os mesmos.
- **A passarela restaurada na Estação Central** (ago/2021–fev/2022) não tem efeito mensurável: razão de 0,90, com intervalo de 95% de 0,34 a 2,13. Com 8 casos depois, só uma queda de mais de dois terços apareceria.

## Pedido

1. **Registrar as obras:** data e local de cada obra do plano, para a próxima avaliação ter um antes e um depois.
2. **Vedação com travessia:** no km 273 e no km 265, a vedação precisa vir junto com uma travessia segura. Em 2019, moradores da Ponte Preta abriram buracos nas grades de proteção para atravessar a linha ([Tribuna de Minas, 2019](https://tribunademinas.com.br/noticias/cidade/11-09-2019/casas-a-beira-da-linha-ferrea-sofrem-rachaduras.html)): vedação sem travessia é vedação aberta de novo.
3. **Saúde mental:** quase metade dos atropelamentos com morte na MRS é registrada como suicídio. A vedação ajuda, mas o tema pede parceria com a rede de saúde mental do município. Este memorando não aponta causa por lugar.

> Se você está passando por um momento difícil, o [CVV](https://cvv.org.br/) atende de graça, 24 horas, pelo telefone **188**.

Painel: https://luissfellipe.github.io/ferrovias-br/juiz-de-fora.html · Notebook: `analises/05_juiz_de_fora.ipynb` · Método: `export/ranking_jf.py`
