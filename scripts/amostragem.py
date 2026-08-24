#!/usr/bin/env python3

import sys
import math
import statistics
import subprocess


# ============================================================
# Configuração do experimento
# ============================================================

# Número fixo de execuções realizadas para cada tamanho
# de problema.
NUM_AMOSTRAS = 30

# Valor crítico da distribuição t de Student para um
# intervalo de confiança bilateral de 95%, considerando
# n = 30 amostras:
#
#     graus de liberdade = n - 1 = 29
#
T_95_29 = 2.045

# Critério adotado para considerar a estimativa da média
# suficientemente precisa.
#
# 0.02 significa que a semilargura do intervalo de confiança
# de 95% deve ser menor ou igual a 2% da média.
#
ERRO_RELATIVO_MAXIMO = 0.02


def executar(executavel, tamanho):
    """
    Executa o programa para um determinado tamanho de problema.

    O programa deve produzir uma linha no formato:

        nome,tamanho,tempo

    Exemplo:

        gerson,1000000,1.059880

    O tempo deve estar expresso em milissegundos.
    """

    resultado = subprocess.run(
        [executavel, str(tamanho)],
        capture_output=True,
        text=True,
        check=True
    )

    linha = resultado.stdout.strip()
    campos = linha.split(",")

    if len(campos) != 3:
        raise ValueError(
            f"Saída inesperada do programa: {linha}"
        )

    tamanho_retornado = int(campos[1])

    if tamanho_retornado != tamanho:
        raise ValueError(
            f"Tamanho retornado ({tamanho_retornado}) "
            f"diferente do solicitado ({tamanho})."
        )

    tempo = float(campos[2])

    return tempo


def calcular_estatisticas(amostras):
    """
    Calcula as estatísticas utilizadas para avaliar a precisão
    da estimativa do tempo médio.

    São calculados:

      - média amostral;
      - desvio padrão amostral;
      - erro padrão da média;
      - intervalo de confiança de 95% da média;
      - margem de erro relativa.

    O intervalo de confiança é calculado por:

        média +- t * s / sqrt(n)

    onde:

        t = valor crítico da distribuição t de Student
        s = desvio padrão amostral
        n = número de amostras
    """

    n = len(amostras)

    media = statistics.mean(amostras)
    desvio = statistics.stdev(amostras)

    erro_padrao = desvio / math.sqrt(n)

    margem = T_95_29 * erro_padrao

    ic_inferior = media - margem
    ic_superior = media + margem

    # A margem de erro relativa indica o tamanho da
    # semilargura do intervalo de confiança em relação
    # à média.
    erro_relativo = margem / media

    return (
        media,
        desvio,
        ic_inferior,
        ic_superior,
        erro_relativo
    )


def main():

    if len(sys.argv) < 3:
        print(
            f"Uso: {sys.argv[0]} <executavel> "
            "<tamanho1> [tamanho2 ...]"
        )
        sys.exit(1)

    executavel = sys.argv[1]

    try:
        tamanhos = [int(x) for x in sys.argv[2:]]
    except ValueError:
        print(
            "Erro: os tamanhos dos problemas devem ser "
            "números inteiros.",
            file=sys.stderr
        )
        sys.exit(1)

    # Cabeçalho da saída CSV
    print(
        "tamanho,n,media_ms,desvio_ms,"
        "ic_inferior_ms,ic_superior_ms,"
        "erro_relativo,precisao_adequada"
    )

    for tamanho in tamanhos:

        try:
            amostras = []

            # ------------------------------------------------
            # Coleta das 30 amostras
            # ------------------------------------------------

            for _ in range(NUM_AMOSTRAS):
                tempo = executar(executavel, tamanho)
                amostras.append(tempo)

            # ------------------------------------------------
            # Análise estatística
            # ------------------------------------------------

            (
                media,
                desvio,
                ic_inferior,
                ic_superior,
                erro_relativo
            ) = calcular_estatisticas(amostras)

            # ------------------------------------------------
            # Avaliação da precisão
            #
            # SIM:
            #     a margem de erro do IC de 95% é menor ou
            #     igual a 2% da média.
            #
            # NAO:
            #     a margem de erro é superior a 2%.
            # ------------------------------------------------

            if erro_relativo <= ERRO_RELATIVO_MAXIMO:
                precisao = "SIM"
            else:
                precisao = "NAO"

            # ------------------------------------------------
            # Saída
            # ------------------------------------------------

            print(
                f"{tamanho},"
                f"{NUM_AMOSTRAS},"
                f"{media:.6f},"
                f"{desvio:.6f},"
                f"{ic_inferior:.6f},"
                f"{ic_superior:.6f},"
                f"{erro_relativo * 100:.2f}%,"
                f"{precisao}"
            )

        except Exception as e:
            print(
                f"Erro ao processar tamanho {tamanho}: {e}",
                file=sys.stderr
            )


if __name__ == "__main__":
    main()
