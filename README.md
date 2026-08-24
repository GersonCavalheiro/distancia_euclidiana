# Distância Euclidiana — Avaliação de Desempenho

Este projeto contém duas implementações em C para o cálculo da distância euclidiana entre vetores e scripts para coleta e análise dos tempos de execução.

O objetivo é permitir a realização de experimentos de desempenho de forma sistemática, mantendo separadas a implementação do problema, a coleta das medições e a análise estatística dos resultados.

## Estrutura do projeto

```text
.
├── src/
│   ├── distancia_naive.c
│   ├── distancia_avx.c
│   └── Makefile
│
└── scripts/
    ├── coleta.py
    └── analise.py
```

O diretório `src` contém as implementações em C e o `Makefile` utilizado para compilá-las.

O diretório `scripts` contém os programas Python utilizados para realizar a coleta dos tempos de execução e sua posterior análise estatística.

## Implementações

São fornecidas duas implementações do mesmo problema.

### `distancia_naive`

Implementação direta do cálculo, sem utilização explícita de instruções vetoriais.

Essa versão representa a implementação de referência do problema.

### `distancia_avx`

Implementação otimizada utilizando instruções AVX2/FMA e alocação adequada dos dados em memória.

A disponibilidade das extensões utilizadas pode ser verificada no Linux com:

```bash
lscpu | grep -i flags
```

Entre as *flags* apresentadas devem estar `avx2` e `fma`.

## Compilação

Entre no diretório `src`:

```bash
cd src
```

Compile as duas implementações utilizando:

```bash
make
```

Os executáveis `distancia_naive` e `distancia_avx` serão produzidos conforme definido pelo `Makefile`.

Para remover os arquivos gerados pela compilação:

```bash
make clean
```

## Execução individual

Cada executável recebe como argumento o tamanho do vetor.

Por exemplo:

```bash
./distancia_naive 1000000
```

ou:

```bash
./distancia_avx 1000000
```

A saída possui o formato:

```text
nome,tamanho,tempo
```

onde:

- `nome` identifica o autor da implementação;
- `tamanho` é o tamanho do problema;
- `tempo` é o tempo de execução medido, em milissegundos.

## Coleta dos dados

O script `coleta.py`, localizado no diretório `scripts`, é responsável por executar os experimentos repetidas vezes e registrar os tempos obtidos.

A sintaxe é:

```text
python3 coleta.py n \
    --executaveis EXECUTAVEL [EXECUTAVEL ...] \
    --tamanhos TAMANHO [TAMANHO ...] \
    [--saida ARQUIVO] \
    [--log ARQUIVO]
```

onde:

- `n` é o número de repetições de **cada caso experimental**;
- `--executaveis` informa a lista de executáveis que serão avaliados;
- `--tamanhos` informa os tamanhos de problema considerados;
- `--saida` define o arquivo CSV de saída; se omitido, será utilizado `coleta.csv`;
- `--log` define o arquivo de log; se omitido, será utilizado `coleta.log`.

### Exemplo

Considerando os executáveis gerados no diretório `src`, uma coleta com 30 repetições para cinco tamanhos de problema pode ser executada, a partir do diretório `scripts`, com:

```bash
cd scripts

python3 coleta.py 30 \
    --executaveis ../src/distancia_naive ../src/distancia_avx \
    --tamanhos 1000 10000 100000 1000000 10000000
```

Nesse exemplo existem:

- 2 executáveis;
- 5 tamanhos de problema;
- 30 repetições de cada combinação.

Portanto, são realizados:

\[
2 \times 5 \times 30 = 300
\]

lançamentos dos programas.

A coleta considera o produto cartesiano entre os executáveis e os tamanhos especificados. Em cada rodada, os diferentes casos experimentais são executados de forma intercalada, evitando que todas as repetições de um mesmo caso sejam realizadas consecutivamente.

Essa organização procura reduzir a associação entre um caso experimental e um período específico da coleta, diminuindo a influência de alterações temporais do ambiente de execução sobre um único caso.

### Arquivos produzidos

Por padrão são gerados:

```text
coleta.csv
coleta.log
```

O arquivo `coleta.csv` contém os tempos medidos no formato:

```text
rodada,ordem,executavel,nome,tamanho,tempo_ms
```

Por exemplo:

```text
1,1,distancia_avx,gerson,10000,0.006146
1,2,distancia_naive,gerson,10000,0.009079
1,3,distancia_avx,gerson,1000000,0.875254
```

A coluna `rodada` identifica a repetição do experimento, enquanto `ordem` registra a posição global em que aquela execução ocorreu durante a coleta.

O arquivo `coleta.log` mantém o registro das execuções lançadas.

Os nomes dos arquivos podem ser alterados, por exemplo:

```bash
python3 coleta.py 30 \
    --executaveis ../src/distancia_naive ../src/distancia_avx \
    --tamanhos 1000 10000 100000 1000000 10000000 \
    --saida experimento.csv \
    --log experimento.log
```

Para consultar todas as opções disponíveis:

```bash
python3 coleta.py --help
```

## Análise dos dados

O script `analise.py` recebe o arquivo produzido pela coleta e a lista dos tamanhos que devem ser considerados na análise.

A partir do diretório `scripts`, por exemplo:

```bash
python3 analise.py coleta.csv 1000 10000 100000 1000000 10000000
```

A análise considera separadamente cada combinação entre executável e tamanho de problema.

Entre as análises realizadas estão:

- média, mediana e média aparada;
- desvio padrão e coeficiente de variação;
- mínimo, máximo, quartis e IQR;
- assimetria e curtose;
- identificação de possíveis outliers pelo critério de 1,5 × IQR;
- intervalo de confiança de 95% baseado na distribuição t de Student;
- intervalo de confiança de 95% obtido por bootstrap;
- histogramas;
- boxplots;
- gráficos Q-Q;
- dispersão dos tempos ao longo da coleta;
- análise de tendência temporal;
- correlações de Pearson e Spearman com a ordem das execuções;
- autocorrelação;
- convergência da média acumulada.

Os possíveis outliers são identificados, mas **não são automaticamente removidos das análises**.

## Registro das análises

A cada execução, `analise.py` cria um diretório com nome no formato:

```text
Registro-AAAAMMDD-HHMMSS
```

Por exemplo:

```text
Registro-20260824-160846/
```

Nesse diretório são preservados os dados e resultados correspondentes àquela execução da análise, incluindo:

```text
Registro-20260824-160846/
├── coleta.csv
├── analise.py
├── relatorio.tex
├── estatisticas.csv
├── outliers.csv
├── autocorrelacao.csv
├── dispersao.jpg
├── boxplot.jpg
├── histogramas/
├── qqplots/
└── convergencia/
```

O arquivo `coleta.csv` original é copiado para o registro, permitindo identificar exatamente os dados que deram origem à análise.

Uma cópia da versão de `analise.py` utilizada também é preservada.

## Relatório

O arquivo:

```text
relatorio.tex
```

contém o relatório da análise realizada, incluindo tabelas com as estatísticas calculadas e referências aos gráficos produzidos.

Para gerar o PDF, entre no diretório do registro e compile o documento LaTeX. Por exemplo:

```bash
cd Registro-20260824-160846
pdflatex relatorio.tex
pdflatex relatorio.tex
```

O resultado será:

```text
relatorio.pdf
```

## Dependências

Para compilação das implementações em C é necessário um compilador compatível com as extensões utilizadas pela versão AVX.

Para os scripts Python é necessário Python 3 e `matplotlib`.

Caso `matplotlib` não esteja instalado:

```bash
python3 -m pip install matplotlib
```

É recomendável utilizar um ambiente virtual Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install matplotlib
```

Para gerar o relatório em PDF é necessária uma instalação LaTeX contendo os pacotes utilizados por `relatorio.tex`.

## Fluxo de utilização

O fluxo normal do experimento é:

```text
src/distancia_naive.c ─┐
                       ├──> make ──> executáveis
src/distancia_avx.c ───┘
                            |
                            v
                    scripts/coleta.py
                            |
                            v
                        coleta.csv
                            |
                            v
                    scripts/analise.py
                            |
                            v
                Registro-AAAAMMDD-HHMMSS
                            |
                            v
               estatísticas + gráficos
                            |
                            v
                      relatorio.tex
```

Dessa forma, os dados brutos permanecem associados aos resultados estatísticos e ao relatório produzido a partir deles.
